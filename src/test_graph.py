"""
Offline test for graph.py.

langgraph isn't installed in this sandbox (PyPI unreachable), so we stub
just enough of it - a minimal fake StateGraph that supports add_node,
add_edge, set_entry_point, and compile().invoke() by walking edges
sequentially (sufficient since our graph is a straight linear chain, no
branching/conditional edges). This lets us verify the actual thing worth
testing: that build_graph() wires the 7 nodes in the correct order and that
state flows through correctly - without needing real API keys or network.

Run with: python3 src/test_graph.py
"""

import sys
import types
from unittest.mock import MagicMock

# --- Minimal fake langgraph.graph module ---
langgraph_stub = types.ModuleType("langgraph")
langgraph_graph_stub = types.ModuleType("langgraph.graph")

END = object()


class FakeCompiledGraph:
    def __init__(self, node_order, nodes):
        self.node_order = node_order
        self.nodes = nodes

    def invoke(self, initial_state):
        state = initial_state
        for name in self.node_order:
            state = self.nodes[name](state)
        return state


class FakeStateGraph:
    def __init__(self, state_schema):
        self.state_schema = state_schema
        self.nodes = {}
        self.edges = []  # list of (from, to) tuples
        self.entry_point = None

    def add_node(self, name, fn):
        self.nodes[name] = fn

    def add_edge(self, from_node, to_node):
        self.edges.append((from_node, to_node))

    def set_entry_point(self, name):
        self.entry_point = name

    def compile(self):
        # Walk edges from entry_point to build a linear execution order.
        # Sufficient for our graph since it has no branching.
        order = [self.entry_point]
        current = self.entry_point
        edge_map = dict(self.edges)
        while current in edge_map and edge_map[current] is not END:
            current = edge_map[current]
            order.append(current)
        return FakeCompiledGraph(order, self.nodes)


langgraph_graph_stub.StateGraph = FakeStateGraph
langgraph_graph_stub.END = END
langgraph_stub.graph = langgraph_graph_stub
sys.modules["langgraph"] = langgraph_stub
sys.modules["langgraph.graph"] = langgraph_graph_stub

# --- Stub the other unavailable-in-sandbox packages, same pattern as earlier tests ---
pydantic_stub = types.ModuleType("pydantic")


class _FakeBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


pydantic_stub.BaseModel = _FakeBaseModel
pydantic_stub.Field = lambda *a, **k: None
sys.modules["pydantic"] = pydantic_stub

langchain_groq_stub = types.ModuleType("langchain_groq")
langchain_groq_stub.ChatGroq = MagicMock()
sys.modules["langchain_groq"] = langchain_groq_stub

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

import os

os.environ["GROQ_API_KEY"] = "fake-key-for-offline-test"

import graph as graph_module  # noqa: E402


def test_build_graph_wires_nodes_in_correct_order():
    call_order = []

    # Patch every node function graph.py imported into its own namespace,
    # so build_graph()'s closures call our recording stubs instead of the
    # real (network/LLM-dependent) implementations.
    def make_recorder(name, extra_state=None):
        def recorder(state):
            call_order.append(name)
            if extra_state:
                state.update(extra_state)
            return state
        return recorder

    graph_module.GitHubClient = MagicMock(
        return_value=MagicMock(
            fetch_open_issues=MagicMock(
                side_effect=lambda *a, **k: (call_order.append("fetch_issues"), [])[1]
            ),
        )
    )
    graph_module.issue_understanding_node = make_recorder("understand_issues", {"enriched_issues": []})
    graph_module.build_repo_index = MagicMock(
        side_effect=lambda *a, **k: (call_order.append("build_index"), "fake_index")[1]
    )
    graph_module.code_context_node = MagicMock(side_effect=lambda state, index: (call_order.append("code_context"), state)[1])
    graph_module.difficulty_scoring_node = make_recorder("difficulty_scoring")
    graph_module.personalized_ranking_node = make_recorder("personalized_ranking", {"final_ranked_list": []})
    graph_module.starting_point_node = MagicMock(
        side_effect=lambda state, client, owner, name, top_n: (call_order.append("starting_point"), state)[1]
    )

    skill_profile = {
        "languages": ["Python"], "frameworks": [], "experience_level": "beginner",
        "time_available": "few hours", "interests": [],
    }

    compiled = graph_module.build_graph("fake_owner", "fake_repo", skill_profile, max_issues=5, top_n_starting_points=3)
    final_state = compiled.invoke({})

    expected_order = [
        "fetch_issues", "understand_issues", "build_index", "code_context",
        "difficulty_scoring", "personalized_ranking", "starting_point",
    ]
    assert call_order == expected_order, f"Wrong execution order.\nExpected: {expected_order}\nGot: {call_order}"
    assert final_state["repo_owner"] == "fake_owner"
    assert final_state["skill_profile"]["experience_level"] == "beginner"
    assert "final_ranked_list" in final_state

    print("PASS: build_graph wires all 7 nodes in the correct linear order.")
    print(f"  Verified order: {' -> '.join(call_order)}")


if __name__ == "__main__":
    test_build_graph_wires_nodes_in_correct_order()
    print("\nAll offline tests passed.")