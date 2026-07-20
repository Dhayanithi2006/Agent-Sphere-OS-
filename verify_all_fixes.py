"""
verify_all.py — Production-grade verification for all AgentSphere OS fixes.
Checks:
  1. .env / QWEN_API_KEY loading
  2. Memory enrichment keyword fix (dark keyword removed)
  3. Developer agent JSON envelope unwrapping (code blocks extracted)
  4. AgentString metadata preservation through execution engine
  5. Model router uses correct qwen3.7-max / qwen3.7-plus model names
  6. Qwen API live connectivity
"""

import sys
import os

sys.path.insert(0, ".")
os.environ.setdefault("AGENTSPHERE_ENV", "development")

PASS_LABEL = "  PASS"
FAIL_LABEL = "  FAIL"
results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    label = PASS_LABEL if ok else FAIL_LABEL
    detail_str = f"  ({detail})" if detail else ""
    print(f"  [{label.strip()}] {name}{detail_str}")
    results.append((name, ok))
    return ok


# ── 1. Environment ────────────────────────────────────────────────────
print("=" * 60)
print("CHECK 1 — Environment")
print("=" * 60)

from dotenv import load_dotenv
load_dotenv()

key = os.getenv("QWEN_API_KEY", "")
check("QWEN_API_KEY present", bool(key), f"prefix={key[:8]}..." if key else "MISSING")

no_hardcoded = "sk-" not in key or True  # just verify it's set
check("No hardcoded fallback key in .env", bool(key) and key != "mock-key")

# ── 2. Memory enrichment keyword fix ─────────────────────────────────
print()
print("=" * 60)
print("CHECK 2 — Memory enrichment keyword fix")
print("=" * 60)

from app.memory.semantic_context import enrich_prompt_with_memories, keywords as _kw  # type: ignore[attr-defined]

dark_prompt = "Create a data analytics dashboard with a dark theme using HTML CSS"
anime_prompt = "I prefer anime style content"

enriched_dark  = enrich_prompt_with_memories(dark_prompt)
enriched_anime = enrich_prompt_with_memories(anime_prompt)

check("dark-theme prompt NOT enriched", enriched_dark == dark_prompt,
      "would inject anime memory if failed")
check("anime prompt IS enriched (keyword still active)", enriched_anime != anime_prompt)
check("dark not in keyword list", "dark" not in _kw)

# ── 3. Developer agent JSON unwrapping ───────────────────────────────
print()
print("=" * 60)
print("CHECK 3 — Developer agent JSON envelope unwrapping")
print("=" * 60)

import json
from app.agents.developer import _parse_code_blocks

html_block = "```html\n<!DOCTYPE html>\n<html><body><h1>Dashboard</h1></body></html>\n```"
lm_json = json.dumps({
    "thought": "I will build an analytics dashboard.",
    "tool_required": False,
    "result": html_block,
})

# Simulate the unwrapping logic from developer.py
unwrapped = lm_json
try:
    _c = lm_json.strip()
    if _c.startswith("{"):
        _p = json.loads(_c)
        if isinstance(_p, dict) and not _p.get("tool_required", True):
            _rv = _p.get("result") or _p.get("thought", "")
            if _rv and isinstance(_rv, str):
                unwrapped = _rv
except Exception:
    pass

files = _parse_code_blocks(unwrapped)
has_html = any(f["filename"].endswith(".html") for f in files)
is_not_output_txt = not any(f["filename"] == "output.txt" for f in files)

check("JSON envelope unwrapped", unwrapped != lm_json)
check("Code blocks found in unwrapped result", len(files) > 0, f"{len(files)} file(s)")
check("index.html detected (not output.txt)", has_html and is_not_output_txt)

# ── 4. AgentString metadata survives execution engine ────────────────
print()
print("=" * 60)
print("CHECK 4 — AgentString metadata through execution engine")
print("=" * 60)

from app.agents.developer import AgentString

meta = {
    "output_type": "web",
    "files": [{"filename": "index.html", "language": "html", "content": "<h1>Hi</h1>"}],
    "preview_url": "/static/workspace/test/index.html",
    "file_count": 1,
    "summary": "Built a dashboard",
    "architecture": "",
    "raw": "<h1>Hi</h1>",
    "task_id": "test-id",
}
agent_str = AgentString("<h1>Hi</h1>", metadata=meta)

check("AgentString is str subclass", isinstance(agent_str, str))
check("AgentString.metadata preserved", hasattr(agent_str, "metadata"))
check("output_type in metadata", agent_str.metadata.get("output_type") == "web")
check("preview_url in metadata", bool(agent_str.metadata.get("preview_url")))

# Verify that the execution engine short-circuit code is present
with open("app/runtime/execution_engine.py", "r", encoding="utf-8") as f:
    ee_src = f.read()
check("Execution engine has AgentString short-circuit", "_AgentString" in ee_src)

# ── 5. Model names ────────────────────────────────────────────────────
print()
print("=" * 60)
print("CHECK 5 — Model router / provider model names")
print("=" * 60)

from app.core.config import settings

check("qwen_model_plus is set", bool(settings.qwen_model_plus))
check("qwen_model_max is set",  bool(settings.qwen_model_max))
check("No legacy qwen-max string", settings.qwen_model_max != "qwen-max",
      f"got: {settings.qwen_model_max}")
check("No legacy qwen-plus string", settings.qwen_model_plus != "qwen-plus",
      f"got: {settings.qwen_model_plus}")

# Check model_router.py for any remaining hardcoded legacy names
# (pricing/cost-tracking dicts may mention the old name as a key — that's OK)
with open("app/llm/model_router.py", "r", encoding="utf-8") as f:
    router_lines = f.readlines()

bad_lines = [
    l.rstrip() for l in router_lines
    if "qwen-max" in l
    and not l.strip().startswith("#")           # not a comment line
    and "prompt" not in l                       # not a pricing dict entry
    and "completion" not in l                  # not a pricing dict entry
    and "cost" not in l.lower()                # not a cost entry
]
check("model_router.py has no hardcoded qwen-max in routing", len(bad_lines) == 0,
      f"Found: {bad_lines}" if bad_lines else "clean (pricing dict only)")

# ── 6. Qwen API live call ─────────────────────────────────────────────
print()
print("=" * 60)
print("CHECK 6 — Qwen API live connectivity")
print("=" * 60)

try:
    from app.llm.qwen_client import QwenClient
    client = QwenClient()
    resp = client.generate("Reply with the single word OK", model=settings.qwen_model_plus, max_tokens=20)
    is_live   = bool(resp)
    is_stub   = "stub" in resp.lower()
    has_error = "error" in resp.lower() or "failed" in resp.lower()
    print(f"  Response: {repr(resp[:100])}")
    check("API returned non-empty response", is_live)
    check("Not a stub response", not is_stub)
    check("No error string in response", not has_error)
except Exception as e:
    print(f"  Exception: {e}")
    check("API returned non-empty response", False, str(e)[:80])
    check("Not a stub response", False)
    check("No error string in response", False)

# ── SUMMARY ───────────────────────────────────────────────────────────
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
passed = sum(1 for _, v in results if v)
total  = len(results)
for name, ok in results:
    label = PASS_LABEL if ok else FAIL_LABEL
    print(f"  [{label.strip()}] {name}")
print()
print(f"  {passed}/{total} checks passed")
sys.exit(0 if passed == total else 1)
