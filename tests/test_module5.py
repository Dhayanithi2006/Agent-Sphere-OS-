from app.dependency.dependency_manager import DependencyManager


def test_dependency_manager_reports_downstream_agents():
    manager = DependencyManager()
    manager.add_dependency("planner", "research")
    manager.add_dependency("research", "developer")
    manager.add_dependency("developer", "tester")
    manager.add_dependency("tester", "reviewer")

    affected = manager.get_affected_agents("developer")
    assert affected == {"tester", "reviewer"}
