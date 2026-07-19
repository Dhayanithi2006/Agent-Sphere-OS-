"""Unit and integration tests for Module 15 (Process Sandbox)."""

from __future__ import annotations

from typing import Any
import pytest
from app.security.sandbox import ProcessSandbox


def test_safe_code_execution_and_inputs():
    """Verify that safe Python code runs successfully and returns variables."""
    sandbox = ProcessSandbox()
    code = "result = (x + y) * 2"
    inputs = {"x": 10, "y": 20}

    res = sandbox.run_sandboxed(code, inputs=inputs)
    assert res.success is True
    assert res.outputs["x"] == 10
    assert res.outputs["y"] == 20
    assert res.outputs["result"] == 60
    assert res.error is None


def test_direct_imports_blocked():
    """Verify that direct module imports are statically blocked by the AST check."""
    sandbox = ProcessSandbox()

    # Direct import
    res1 = sandbox.run_sandboxed("import os")
    assert res1.success is False
    assert "Direct imports are restricted" in res1.error

    # From import
    res2 = sandbox.run_sandboxed("from sys import exit")
    assert res2.success is False
    assert "imports from packages are restricted" in res2.error


def test_restricted_builtins_blocked():
    """Verify that dangerous built-ins (open, eval, exec) are not defined in scope."""
    sandbox = ProcessSandbox()

    # Try open file
    res1 = sandbox.run_sandboxed("f = open('test.txt', 'w')")
    assert res1.success is False
    assert "name 'open' is not defined" in res1.error

    # Try eval
    res2 = sandbox.run_sandboxed("eval('1 + 1')")
    assert res2.success is False
    assert "name 'eval' is not defined" in res2.error


def test_double_underscore_access_blocked():
    """Verify that variable or attribute access with double underscores is blocked."""
    sandbox = ProcessSandbox()

    # Double underscore variable
    res1 = sandbox.run_sandboxed("__my_var__ = 10")
    assert res1.success is False
    assert "Double underscore variable name" in res1.error

    # Class inheritance traversal bypass attempt
    res2 = sandbox.run_sandboxed("x = ().__class__.__bases__[0]")
    assert res2.success is False
    assert "Accessing double underscore attribute" in res2.error


def test_execution_timeout_triggering():
    """Verify that infinite loop executions are terminated by the timeout gate."""
    sandbox = ProcessSandbox()
    infinite_loop_code = """
x = 0
while True:
    x += 1
"""

    res = sandbox.run_sandboxed(infinite_loop_code, timeout=0.1)
    assert res.success is False
    assert res.timeout_triggered is True
    assert "Sandbox Execution Timeout" in res.error
