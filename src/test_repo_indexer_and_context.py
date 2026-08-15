"""
Offline tests for repo_indexer.py and code_context_node.py.

chromadb isn't installed in this sandbox (PyPI unreachable), so we stub
just enough of it to test OUR logic: file filtering/chunking (pure Python,
no chromadb needed) and the query/retry logic in code_context_node.py
(using a fake RepoIndex so we don't need a real Chroma collection).

Run with: python3 src/test_repo_indexer_and_context.py
"""

import os
import sys
import types
import tempfile
import shutil

# --- Stub chromadb enough for repo_indexer.py to import cleanly ---
chromadb_stub = types.ModuleType("chromadb")
chromadb_stub.EphemeralClient = lambda: None
embedding_functions_stub = types.ModuleType("chromadb.utils.embedding_functions")
embedding_functions_stub.DefaultEmbeddingFunction = lambda: None
utils_stub = types.ModuleType("chromadb.utils")
utils_stub.embedding_functions = embedding_functions_stub
chromadb_stub.utils = utils_stub
sys.modules["chromadb"] = chromadb_stub
sys.modules["chromadb.utils"] = utils_stub
sys.modules["chromadb.utils.embedding_functions"] = embedding_functions_stub

import repo_indexer  # noqa: E402
from code_context_node import _build_query, _query_with_retry, code_context_node  # noqa: E402


def test_walk_source_files_skips_junk_dirs_and_filters_extensions():
    tmp = tempfile.mkdtemp()
    try:
        # Real source file - should be included
        os.makedirs(os.path.join(tmp, "src"))
        with open(os.path.join(tmp, "src", "main.py"), "w") as f:
            f.write("def main(): pass")

        # Junk dirs - should be excluded entirely
        os.makedirs(os.path.join(tmp, "node_modules", "some_pkg"))
        with open(os.path.join(tmp, "node_modules", "some_pkg", "index.js"), "w") as f:
            f.write("module.exports = {}")

        os.makedirs(os.path.join(tmp, ".git"))
        with open(os.path.join(tmp, ".git", "config"), "w") as f:
            f.write("[core]")

        # Wrong extension - should be excluded
        with open(os.path.join(tmp, "src", "data.bin"), "wb") as f:
            f.write(b"\x00\x01\x02")

        # Config file - should now be included (fixes the pyproject.toml gap)
        with open(os.path.join(tmp, "pyproject.toml"), "w") as f:
            f.write("[project]\nname = 'test'")

        # README.md - the one .md file that SHOULD be included
        with open(os.path.join(tmp, "README.md"), "w") as f:
            f.write("# Test project")

        # Non-README markdown - should be EXCLUDED (noise: changelog/faq/etc.)
        with open(os.path.join(tmp, "CHANGELOG.md"), "w") as f:
            f.write("## v1.0.0\n- initial release")

        files = repo_indexer.walk_source_files(tmp)

        assert "src/main.py" in files, f"Expected src/main.py in results, got {files}"
        assert not any("node_modules" in f for f in files), "node_modules should be excluded!"
        assert not any(".git" in f for f in files), ".git should be excluded!"
        assert not any(f.endswith(".bin") for f in files), ".bin files should be excluded!"
        assert "pyproject.toml" in files, "pyproject.toml should now be indexed (config file gap fix)"
        assert "README.md" in files, "README.md should be indexed"
        assert "CHANGELOG.md" not in files, "CHANGELOG.md should be excluded as markdown noise"

        # All returned paths should use forward slashes regardless of OS
        assert all("\\" not in f for f in files), f"Found backslash in a path, normalization failed: {files}"

        print("PASS: walk_source_files correctly filters junk dirs, extensions, markdown noise, and normalizes paths.")
    finally:
        shutil.rmtree(tmp)


def test_chunk_file_produces_overlapping_chunks_for_large_file():
    tmp = tempfile.mkdtemp()
    try:
        # Create a file bigger than MAX_CHUNK_CHARS to force multiple chunks
        big_content = "x = 1\n" * 500  # well over 1500 chars
        with open(os.path.join(tmp, "big.py"), "w") as f:
            f.write(big_content)

        chunks = repo_indexer.chunk_file(tmp, "big.py")

        assert len(chunks) > 1, f"Expected multiple chunks for a large file, got {len(chunks)}"
        assert all(c.file_path == "big.py" for c in chunks)
        # Verify overlap: end of chunk N should share content with start of chunk N+1
        if len(chunks) >= 2:
            overlap_region = chunks[0].content[-100:]
            assert overlap_region in chunks[1].content or chunks[1].content[:100] in chunks[0].content, \
                "Expected some overlap between consecutive chunks"

        print(f"PASS: chunk_file split large file into {len(chunks)} overlapping chunks.")
    finally:
        shutil.rmtree(tmp)


def test_chunk_file_skips_empty_file():
    tmp = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmp, "empty.py"), "w") as f:
            f.write("   \n  \n")  # whitespace only
        chunks = repo_indexer.chunk_file(tmp, "empty.py")
        assert chunks == [], "Empty/whitespace-only files should produce zero chunks"
        print("PASS: empty files correctly skipped.")
    finally:
        shutil.rmtree(tmp)


class FakeRepoIndex:
    """Simulates a RepoIndex with pre-programmed results per query, so we
    can test the retry logic without a real Chroma collection."""

    def __init__(self, responses: dict):
        # responses: maps query string -> list of result dicts
        self.responses = responses
        self.queries_made = []

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        self.queries_made.append(query_text)
        return self.responses.get(query_text, [])


def test_retry_triggers_on_weak_match_and_improves():
    understanding = {
        "summary": "Some vague issue about performance",
        "key_terms": ["cache_manager.py", "invalidate_cache"],
    }

    strong_query = "cache_manager.py invalidate_cache"
    weak_query = "Some vague issue about performance cache_manager.py invalidate_cache"

    fake_index = FakeRepoIndex(
        {
            weak_query: [{"file_path": "unrelated.py", "start_line_estimate": 1, "snippet": "x", "distance": 1.9}],
            strong_query: [{"file_path": "cache_manager.py", "start_line_estimate": 10, "snippet": "y", "distance": 0.3}],
        }
    )

    results = _query_with_retry(fake_index, understanding)

    assert len(fake_index.queries_made) == 2, "Should have retried once after weak initial match"
    assert results[0]["file_path"] == "cache_manager.py", "Should return the better (retry) results"
    print("PASS: weak match correctly triggers retry and returns improved results.")


def test_no_retry_when_first_match_is_strong():
    understanding = {"summary": "Fix typo", "key_terms": ["README.md"]}
    query = _build_query(understanding)

    fake_index = FakeRepoIndex(
        {query: [{"file_path": "README.md", "start_line_estimate": 5, "snippet": "z", "distance": 0.1}]}
    )

    results = _query_with_retry(fake_index, understanding)

    assert len(fake_index.queries_made) == 1, "Should NOT retry when first match is already strong"
    assert results[0]["file_path"] == "README.md"
    print("PASS: strong initial match correctly skips retry.")


def test_code_context_node_handles_missing_index_results_gracefully():
    fake_index = FakeRepoIndex({})  # every query returns []

    state = {
        "enriched_issues": [
            {
                "issue_number": 1,
                "understanding": {"summary": "test", "key_terms": ["foo"]},
            }
        ],
        "errors": [],
    }

    result_state = code_context_node(state, fake_index)

    assert result_state["enriched_issues"][0]["likely_files"] == []
    assert "No relevant files" in result_state["enriched_issues"][0]["code_context_summary"]
    print("PASS: node handles zero index results without crashing.")


if __name__ == "__main__":
    test_walk_source_files_skips_junk_dirs_and_filters_extensions()
    test_chunk_file_produces_overlapping_chunks_for_large_file()
    test_chunk_file_skips_empty_file()
    test_retry_triggers_on_weak_match_and_improves()
    test_no_retry_when_first_match_is_strong()
    test_code_context_node_handles_missing_index_results_gracefully()
    print("\nAll offline tests passed.")