"""
repo_indexer.py

Clones a target repo locally and builds a searchable vector index of its
source files using ChromaDB with a LOCAL embedding model (all-MiniLM-L6-v2,
runs via ONNX on CPU - no API key, no cost, no external calls after the
one-time model download).

This is built once per repo (not once per issue) - the resulting index is
reused by code_context_node.py to search for files relevant to each issue.
"""

import os
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass

import chromadb
from chromadb.utils import embedding_functions

# Directories we never want to index - vendored code, build artifacts, deps
SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
    ".tox", "vendor", "site-packages", ".mypy_cache", ".pytest_cache", "egg-info",
}

# File types worth indexing. Extend this list if targeting non-Python repos.
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb",
    ".toml", ".cfg", ".ini", ".yaml", ".yml",
}

MAX_CHUNK_CHARS = 1500
CHUNK_OVERLAP_CHARS = 200


@dataclass
class CodeChunk:
    file_path: str       # path relative to repo root
    content: str
    start_line_estimate: int


def _force_remove_readonly(func, path, exc_info):
    """
    shutil.rmtree error handler for Windows: git marks internal files
    (e.g. .git/objects/pack/*.idx) as read-only, which makes Windows refuse
    to delete them. This clears the read-only attribute and retries the
    same operation. No-op-safe on other platforms too.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clone_repo(owner: str, repo: str, dest_dir: str) -> str:
    """
    Shallow-clones a public repo. Returns the path it was cloned into.
    Raises RuntimeError on failure (private repo, doesn't exist, network issue).
    """
    repo_path = os.path.join(dest_dir, f"{owner}__{repo}")
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path, onerror=_force_remove_readonly)

    url = f"https://github.com/{owner}/{repo}.git"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", url, repo_path],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed for {owner}/{repo}: {result.stderr}")

    return repo_path


def walk_source_files(repo_path: str) -> list[str]:
    """Returns a list of relevant source file paths (relative to repo_path)."""
    matches = []
    for root, dirs, files in os.walk(repo_path):
        # prune skip dirs in-place so os.walk doesn't descend into them
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            ext = os.path.splitext(fname)[1]
            # Markdown is handled specially: most .md files (CHANGELOG,
            # FAQ, contributing guides, GitHub issue-template question
            # snippets in a "questions/" folder, etc.) add noise rather
            # than signal for code-matching purposes. README.md is the
            # one exception - it's occasionally exactly what an issue is
            # about, so we keep it.
            if ext == ".md":
                if fname.lower() != "readme.md":
                    continue
            elif ext not in SOURCE_EXTENSIONS:
                continue

            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, repo_path)
            # Normalize to forward slashes regardless of OS - keeps paths
            # consistent with GitHub URLs and safe for the future React
            # frontend, even though os.path.join gives backslashes on Windows.
            rel_path = rel_path.replace(os.sep, "/")
            matches.append(rel_path)
    return matches


def chunk_file(repo_path: str, rel_path: str) -> list[CodeChunk]:
    """Reads a file and splits it into overlapping character-based chunks.

    Character-based chunking (rather than trying to parse function/class
    boundaries per-language) keeps this language-agnostic for v1. It's a
    reasonable tradeoff: less "semantically clean" than AST-aware chunking,
    but works identically across Python/JS/Go/etc without per-language parsers.
    """
    full_path = os.path.join(repo_path, rel_path)
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return []

    if not text.strip():
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHUNK_CHARS, len(text))
        chunk_text = text[start:end]
        line_estimate = text[:start].count("\n") + 1
        chunks.append(
            CodeChunk(file_path=rel_path, content=chunk_text, start_line_estimate=line_estimate)
        )
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP_CHARS

    return chunks


class RepoIndex:
    """Wraps a Chroma collection for a single indexed repo."""

    def __init__(self, collection):
        self.collection = collection

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        results = self.collection.query(query_texts=[query_text], n_results=top_k)
        out = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, distances):
            out.append(
                {
                    "file_path": meta.get("file_path"),
                    "start_line_estimate": meta.get("start_line_estimate"),
                    "snippet": doc[:400],  # truncate for prompt-size safety downstream
                    "distance": dist,
                }
            )
        return out


def build_repo_index(owner: str, repo: str, workdir: str = None) -> RepoIndex:
    """
    Full pipeline: clone -> walk -> chunk -> embed -> index.
    Uses an in-memory Chroma client (chromadb.EphemeralClient) since we
    rebuild the index each run - swap to PersistentClient if you want to
    cache indexes across runs for the same repo.

    workdir defaults to the OS's real temp directory (via tempfile.gettempdir())
    rather than a hardcoded "/tmp/..." path, which isn't valid on Windows.
    """
    if workdir is None:
        workdir = os.path.join(tempfile.gettempdir(), "issue-matchmaker-repos")
    os.makedirs(workdir, exist_ok=True)
    repo_path = clone_repo(owner, repo, workdir)

    files = walk_source_files(repo_path)
    if not files:
        raise RuntimeError(f"No source files found in {owner}/{repo} - check SOURCE_EXTENSIONS")

    all_chunks: list[CodeChunk] = []
    for rel_path in files:
        all_chunks.extend(chunk_file(repo_path, rel_path))

    client = chromadb.EphemeralClient()
    embed_fn = embedding_functions.DefaultEmbeddingFunction()  # local ONNX MiniLM, free
    collection = client.create_collection(
        name=f"{owner}_{repo}_index", embedding_function=embed_fn
    )

    # Chroma requires unique string IDs and batches well under a few thousand docs at a time
    ids = [f"{c.file_path}::{i}" for i, c in enumerate(all_chunks)]
    documents = [c.content for c in all_chunks]
    metadatas = [
        {"file_path": c.file_path, "start_line_estimate": c.start_line_estimate}
        for c in all_chunks
    ]

    batch_size = 500
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i : i + batch_size],
            documents=documents[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    return RepoIndex(collection)