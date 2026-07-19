"""Process sandbox for executing untrusted Python code safely with timeout and built-in controls."""

from __future__ import annotations

import ast
import concurrent.futures
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(slots=True)
class SandboxResult:
    """Outcome of a sandboxed execution attempt."""

    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timeout_triggered: bool = False


class SecurityVisitor(ast.NodeVisitor):
    """AST visitor enforcing security checks for sandboxed code."""

    def visit_Name(self, node: ast.Name) -> None:
        if "__" in node.id:
            raise PermissionError(f"Security Violation: Double underscore variable name '{node.id}' is blocked.")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if "__" in node.attr:
            raise PermissionError(f"Security Violation: Accessing double underscore attribute '{node.attr}' is blocked.")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        raise PermissionError("Security Violation: Direct imports are restricted in the sandbox.")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        raise PermissionError("Security Violation: Direct imports from packages are restricted in the sandbox.")


class ProcessSandbox:
    """Restricted Python sandbox enforcing AST scans, limited builtins, and cross-platform timeouts."""

    # Set of safe built-in functions
    RESTRICTED_BUILTINS = {
        "abs": abs,
        "all": all,
        "any": any,
        "bin": bin,
        "bool": bool,
        "chr": chr,
        "dict": dict,
        "divmod": divmod,
        "enumerate": enumerate,
        "float": float,
        "hash": hash,
        "hex": hex,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "oct": oct,
        "ord": ord,
        "pow": pow,
        "range": range,
        "repr": repr,
        "reversed": reversed,
        "round": round,
        "set": set,
        "slice": slice,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
    }

    def _security_ast_check(self, code: str) -> None:
        """Parse source code into an AST and perform static security checks."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise PermissionError(f"Security Scan Blocked: Syntax error in sandbox code: {e}")

        visitor = SecurityVisitor()
        visitor.visit(tree)

    def run_sandboxed(
        self, code: str, inputs: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None
    ) -> SandboxResult:
        """Execute Python code in an isolated scope, checking safety rules and enforcing timeouts."""
        # 1. Run static security audit
        try:
            self._security_ast_check(code)
        except Exception as e:
            return SandboxResult(success=False, error=str(e))

        # 2. Compile code
        try:
            compiled = compile(code, "<sandbox>", "exec")
        except Exception as e:
            return SandboxResult(success=False, error=f"Compilation Error: {e}")

        # 3. Setup execution variables
        globals_dict = {"__builtins__": self.RESTRICTED_BUILTINS}
        locals_dict = dict(inputs or {})

        def execution_worker() -> Dict[str, Any]:
            start_time = time.perf_counter()

            def tracer(frame, event, arg):
                if timeout and (time.perf_counter() - start_time > timeout):
                    raise TimeoutError(f"Sandbox Execution Timeout: Execution exceeded limit of {timeout} seconds.")
                return tracer

            sys.settrace(tracer)
            try:
                exec(compiled, globals_dict, locals_dict)
            finally:
                sys.settrace(None)
            return {k: v for k, v in locals_dict.items() if not k.startswith("__")}

        # 4. Run execution worker with time boundary
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(execution_worker)
            try:
                outputs = future.result(timeout=timeout)
                return SandboxResult(success=True, outputs=outputs)
            except concurrent.futures.TimeoutError:
                return SandboxResult(
                    success=False,
                    error=f"Sandbox Execution Timeout: Execution exceeded limit of {timeout} seconds.",
                    timeout_triggered=True,
                )
            except Exception as e:
                # Extract TimeoutError if it was raised inside the tracing check
                err_msg = str(e)
                timeout_triggered = "Sandbox Execution Timeout" in err_msg
                return SandboxResult(
                    success=False,
                    error=err_msg,
                    timeout_triggered=timeout_triggered,
                )
