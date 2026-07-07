from app.dependency.dependency_manager import DependencyManager


def test_module5_dependency_graph_and_impact():
    manager = DependencyManager()
    manager.add_dependency('planner', 'research')
    manager.add_dependency('developer', 'planner')

    assert manager.get_dependencies('planner') == {'research'}
    assert manager.get_dependents('planner') == {'developer'}
    assert manager.get_affected_agents('research') == {'planner', 'developer'}
