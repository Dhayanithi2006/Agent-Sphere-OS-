"""Developer agent for implementation-oriented tasks."""

from __future__ import annotations

import os
import re
import json
import uuid
from pathlib import Path
from typing import Any


from app.agents.base_agent import BaseAgent

# Root workspace directory where generated files are saved
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent / "static" / "workspace"


def _detect_output_type(prompt: str, code: str) -> str:
    """Detect the type of output to show on the frontend."""
    prompt_lower = prompt.lower()
    code_lower = code.lower()

    # ML / model / architecture
    ml_keywords = ["neural network", "ml model", "machine learning", "deep learning",
                   "architecture", "lstm", "cnn", "transformer", "dataset", "training",
                   "classification", "regression", "model design"]
    if any(k in prompt_lower for k in ml_keywords):
        return "architecture"

    # Web / HTML / CSS / JS
    if any(k in code_lower for k in ["<!doctype", "<html", "<body", "<div", "<form"]):
        return "web"
    if any(k in prompt_lower for k in ["html", "css", "webpage", "web page", "login page",
                                        "landing page", "dashboard", "ui", "interface", "frontend"]):
        return "web"

    # API / backend
    if any(k in prompt_lower for k in ["rest api", "api", "endpoint", "fastapi", "flask", "express"]):
        return "api"

    # Writing / research
    if any(k in prompt_lower for k in ["research", "report", "essay", "article", "summary", "write"]):
        return "writing"

    return "code"


def _parse_code_blocks(raw: str) -> list[dict[str, str]]:
    """Extract fenced code blocks from LLM output.
    Returns a list of {filename, language, content} dicts.
    """
    files: list[dict[str, str]] = []
    # Match ```lang\n...``` with optional filename comment
    pattern = re.compile(
        r"```(?P<lang>\w+)?\s*(?:\n)?(?P<content>.*?)```",
        re.DOTALL,
    )
    lang_to_ext = {
        "html": "html", "css": "css", "javascript": "js", "js": "js",
        "typescript": "ts", "ts": "ts", "python": "py", "py": "py",
        "json": "json", "bash": "sh", "sh": "sh", "sql": "sql",
        "yaml": "yml", "yml": "yml",
    }
    counters: dict[str, int] = {}
    for match in pattern.finditer(raw):
        lang = (match.group("lang") or "txt").lower()
        content = match.group("content").strip()
        if not content:
            continue
        ext = lang_to_ext.get(lang, lang)
        counters[ext] = counters.get(ext, 0) + 1
        n = counters[ext]

        # Try to derive filename from first-line comment e.g. // app.js
        filename = None
        first_line = content.split("\n")[0].strip()
        for prefix in ("//", "#", "<!--", "/*"):
            if first_line.startswith(prefix):
                candidate = first_line.lstrip("/ #<!-*").strip()
                if "." in candidate and len(candidate) < 60:
                    filename = candidate
                break

        if not filename:
            if ext == "html":
                filename = "index.html" if n == 1 else f"page{n}.html"
            elif ext == "css":
                filename = "style.css" if n == 1 else f"style{n}.css"
            elif ext in ("js", "ts"):
                filename = "app.js" if n == 1 else f"script{n}.js"
            elif ext == "py":
                filename = "main.py" if n == 1 else f"module{n}.py"
            else:
                filename = f"file{n}.{ext}"

        files.append({"filename": filename, "language": lang, "content": content})

    # If no code blocks found, treat whole response as a single file
    if not files:
        files.append({"filename": "output.txt", "language": "text", "content": raw.strip()})

    return files


def _generate_mermaid_from_prompt(prompt: str, llm_output: str) -> str:
    """Generate a simple Mermaid architecture diagram from ML-related prompts."""
    lines = [
        "graph TD",
        '    Input["📥 Input Layer"] --> Preprocess["⚙️ Preprocessing"]',
    ]

    prompt_lower = prompt.lower()

    if "cnn" in prompt_lower or "convolutional" in prompt_lower:
        lines += [
            '    Preprocess --> Conv1["🔲 Conv Layer 1\\n(32 filters, 3×3)"]',
            '    Conv1 --> Pool1["↓ MaxPool 2×2"]',
            '    Pool1 --> Conv2["🔲 Conv Layer 2\\n(64 filters, 3×3)"]',
            '    Pool2 --> Flatten["📐 Flatten"]',
            '    Flatten --> FC["💡 Fully Connected\\n(128 neurons)"]',
            '    FC --> Output["📤 Softmax Output"]',
        ]
    elif "lstm" in prompt_lower or "rnn" in prompt_lower or "sequence" in prompt_lower:
        lines += [
            '    Preprocess --> Embed["📝 Embedding Layer"]',
            '    Embed --> LSTM1["🔁 LSTM Layer 1\\n(128 units)"]',
            '    LSTM1 --> LSTM2["🔁 LSTM Layer 2\\n(64 units)"]',
            '    LSTM2 --> Dense["💡 Dense Layer"]',
            '    Dense --> Output["📤 Output"]',
        ]
    elif "transformer" in prompt_lower or "attention" in prompt_lower:
        lines += [
            '    Preprocess --> Embed["📝 Token Embedding + Positional Encoding"]',
            '    Embed --> Attn["🎯 Multi-Head Self-Attention"]',
            '    Attn --> FFN["⚡ Feed-Forward Network"]',
            '    FFN --> Norm["📊 Layer Normalization"]',
            '    Norm --> Output["📤 Output / Decoder"]',
        ]
    else:
        lines += [
            '    Preprocess --> Layer1["💡 Hidden Layer 1\\n(Dense 256)"]',
            '    Layer1 --> Dropout["💧 Dropout (0.3)"]',
            '    Dropout --> Layer2["💡 Hidden Layer 2\\n(Dense 128)"]',
            '    Layer2 --> Output["📤 Output Layer"]',
        ]

    lines += [
        '    style Input fill:#1a1a2e,stroke:#00D4FF,color:#F0F4FF',
        '    style Output fill:#1a1a2e,stroke:#00FF9D,color:#F0F4FF',
    ]
    return "\n".join(lines)


def _write_workspace_files(task_id: str, files: list[dict[str, str]]) -> str:
    """Write generated files to the workspace directory. Returns preview URL."""
    workspace_dir = WORKSPACE_ROOT / task_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        file_path = workspace_dir / f["filename"]
        file_path.write_text(f["content"], encoding="utf-8")

    # Check if there's an HTML file for preview
    html_files = [f for f in files if f["filename"].endswith(".html")]
    if html_files:
        return f"/static/workspace/{task_id}/{html_files[0]['filename']}"
    return ""


class AgentString(str):
    """A string subclass that allows attaching custom metadata (e.g. parsed files) for the UI,
    while still behaving exactly like a string to ensure backward compatibility with the execution engine.
    """
    def __new__(cls, value: str, metadata: dict[str, Any] | None = None) -> AgentString:
        obj = super().__new__(cls, value)
        obj.metadata = metadata or {}
        return obj


class DeveloperAgent(BaseAgent):
    """Produces implementation code, writes files to workspace, and returns structured build output."""

    def __init__(self, model_router=None, **kwargs) -> None:
        super().__init__(agent_id="developer", name="developer")
        self._model_router = model_router

    def _get_router(self):
        if self._model_router:
            return self._model_router
        from app.core.shared import model_router
        return model_router

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        payload = payload or {}
        requirement = payload.get("requirement", "") or payload.get("task", "")
        task_id = payload.get("task_id", str(uuid.uuid4()))

        prompt = f"Implement the following requirement: {requirement}\n\nProvide complete, working code with proper file structure. Use fenced code blocks (```html, ```css, ```javascript, ```python etc.) for each file."
        raw_output = self._get_router().route("developer", prompt)

        # Detect output type
        output_type = _detect_output_type(requirement, raw_output)

        # Parse code blocks
        files = _parse_code_blocks(raw_output)

        # Write files to workspace
        preview_url = _write_workspace_files(task_id, files)

        # Generate architecture diagram for ML prompts
        architecture = ""
        if output_type == "architecture":
            architecture = _generate_mermaid_from_prompt(requirement, raw_output)

        # Build summary (first non-code paragraph)
        summary_lines = []
        for line in raw_output.split("\n"):
            if line.strip() and not line.strip().startswith("```") and not line.startswith("    "):
                summary_lines.append(line.strip())
            if len(summary_lines) >= 3:
                break
        summary = " ".join(summary_lines)[:300] or "Build completed successfully."

        metadata = {
            "output_type": output_type,   # "web" | "api" | "architecture" | "writing" | "code"
            "files": files,               # [{filename, language, content}]
            "preview_url": preview_url,   # e.g. /static/workspace/<task_id>/index.html
            "architecture": architecture, # Mermaid diagram string (for ML prompts)
            "summary": summary,
            "raw": raw_output,
            "task_id": task_id,
            "file_count": len(files),
        }

        return AgentString(raw_output, metadata=metadata)
