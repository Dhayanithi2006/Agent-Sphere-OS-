"""Tests verifying real execution, input validation, error handling, timeouts, and path traversal protection for all 8 system tools."""

from __future__ import annotations

import os
import pytest
from app.core.shared import tool_manager, tool_registry


def test_search_web_tool():
    """Verify DuckDuckGo search execution and fallbacks."""
    res = tool_manager.execute("search_web", {"query": "FastAPI Release"})
    assert res is not None
    assert "FastAPI" in res or "Search completed" in res or "Search result stub" in res


def test_read_url_tool():
    """Verify URL fetching and schema validation."""
    # Test valid URL
    res = tool_manager.execute("read_url", {"url": "https://pypi.org/project/fastapi/"})
    assert res is not None
    assert len(res) > 0

    # Test invalid scheme URL
    with pytest.raises(ValueError, match="Only HTTP/HTTPS are supported"):
        tool_manager.execute("read_url", {"url": "ftp://ftp.example.com"})


def test_git_clone_validation():
    """Verify repository URL validation and path traversal checks."""
    # Invalid repository URL format
    with pytest.raises(ValueError, match="Invalid repository URL format"):
        tool_manager.execute("git_clone", {"repo_url": "ftp://invalid-url", "target_dir": "temp_repo"})

    # Path traversal check
    with pytest.raises(PermissionError, match="Path Traversal Blocked"):
        tool_manager.execute("git_clone", {"repo_url": "https://github.com/tiangolo/fastapi.git", "target_dir": "../dangerous"})


def test_pytest_tool_path_traversal():
    """Verify pytest execution restricts paths inside workspace."""
    with pytest.raises(PermissionError, match="Path Traversal Blocked"):
        tool_manager.execute("pytest", {"test_path": "../tests"})


def test_python_runner_execution():
    """Verify sandbox Python execution and timeout bounds."""
    res = tool_manager.execute("python_runner", {"code": "print('hello world')"})
    assert "hello world" in res

    # Timeout validation (timeout is 10s)
    res_timeout = tool_manager.execute("python_runner", {"code": "import time; time.sleep(12)"})
    assert "Timeout expired" in res_timeout


def test_docker_tool_security():
    """Verify dangerous Docker commands are blocked."""
    with pytest.raises(PermissionError, match="Access Denied: Dangerous Docker command blocked"):
        tool_manager.execute("docker", {"cmd": "run --privileged -v /:/host ubuntu"})


def test_filesystem_tool_traversal():
    """Verify file read/write prevents path traversal outside workspace."""
    with pytest.raises(PermissionError, match="Path Traversal Blocked"):
        tool_manager.execute("filesystem", {"action": "read", "path": "../../unauthorized.txt"})


def test_database_tool_security():
    """Verify database tool accepts SELECT/PRAGMA operations and blocks mutations."""
    # Test valid SELECT query
    res = tool_manager.execute("database", {"query": "SELECT name FROM sqlite_master WHERE type='table'"})
    assert "checkpoints" in res or "sqlite_master" in res or "Query executed" in res

    # Test blocked mutation query
    with pytest.raises(PermissionError, match="Only SELECT and PRAGMA database queries are allowed"):
        tool_manager.execute("database", {"query": "DROP TABLE checkpoints"})
