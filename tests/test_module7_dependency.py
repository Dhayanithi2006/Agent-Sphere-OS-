"""Unit and integration tests for Module 7 (Dependency Manager)."""

from __future__ import annotations

import pytest
from app.dependency.dependency_manager import DependencyManager


@pytest.fixture
def clean_manager() -> DependencyManager:
    """Fixture providing a fresh isolated DependencyManager instance."""
    return DependencyManager()


def test_dependency_crud_operations(clean_manager):
    """Verify adding, checking, and removing direct dependency edges."""
    manager = clean_manager

    # Add dependencies: A depends on B, B depends on C
    manager.add_dependency("A", "B")
    manager.add_dependency("B", "C")

    # Assert nodes and edges are populated
    assert manager.get_nodes() == ["A", "B", "C"]
    assert manager.get_edges() == [("A", "B"), ("B", "C")]

    # Assert direct relations
    assert manager.get_dependencies("A") == {"B"}
    assert manager.get_dependents("B") == {"A"}

    # Remove edge
    manager.remove_dependency("A", "B")
    assert manager.get_edges() == [("B", "C")]
    assert manager.get_dependencies("A") == set()


def test_cycle_detection(clean_manager):
    """Verify that cycles are detected and topological sorting raises ValueError."""
    manager = clean_manager

    manager.add_dependency("A", "B")
    manager.add_dependency("B", "C")
    
    # Assert DAG is acyclic initially
    assert manager.has_cycle() is False

    # Create cycle: C depends on A
    manager.add_dependency("C", "A")
    assert manager.has_cycle() is True

    # Assert topological sorting raises ValueError when a cycle is present
    with pytest.raises(ValueError, match="Dependency graph contains a cycle"):
        manager.topological_sort()


def test_topological_sorting(clean_manager):
    """Verify correct linear ordering of vertices in topological sort."""
    manager = clean_manager

    # Construct DAG: reviewer depends on tester, tester depends on developer, developer on researcher
    manager.add_dependency("reviewer", "tester")
    manager.add_dependency("tester", "developer")
    manager.add_dependency("developer", "researcher")

    # Under topological sorting, the nodes must run in order of no dependencies first
    # So researcher runs first, then developer, then tester, then reviewer
    ordered = manager.topological_sort()
    assert ordered == ["researcher", "developer", "tester", "reviewer"]


def test_affected_agents_downstream(clean_manager):
    """Verify identification of downstream nodes affected by an agent's failure."""
    manager = clean_manager

    manager.add_dependency("planner", "researcher")
    manager.add_dependency("researcher", "developer")
    manager.add_dependency("developer", "tester")
    manager.add_dependency("tester", "reviewer")

    # If developer fails, tester is affected downstream
    # Let's verify affected walk outputs (compatibility fallback)
    affected = manager.get_affected_agents("developer")
    assert "tester" in affected



def test_visualization_exporters(clean_manager):
    """Verify Dot and pyvis HTML visualizer generation outputs."""
    manager = clean_manager
    manager.add_dependency("planner", "researcher")

    # Check Dot string
    dot_str = manager.to_dot()
    assert "planner" in dot_str
    assert "researcher" in dot_str

    # Check Pyvis HTML generation
    html_str = manager.to_html()
    assert "<html" in html_str.lower()
    assert "AgentSphere OS" in html_str
