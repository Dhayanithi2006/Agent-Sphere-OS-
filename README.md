# AgentSphere OS — Project Overview & Developer Agent Onboarding

Welcome to **AgentSphere OS**, a runtime environment that treats AI agents like operating system processes. This document provides a comprehensive mental model, architectural breakdown, current build status, and onboarding instructions for developer agents or LLMs working on this codebase.

---

## 1. What AgentSphere OS Is (Mental Model)

AgentSphere OS is **not** a simple sequential agent wrapper or pipeline. It is a stateful runtime designed to orchestrate, track, checkpoint, and dynamically recover multi-agent workflows.

| OS Metaphor | AgentSphere OS Implementation | Description |
| :--- | :--- | :--- |
| **Processes** | `BaseAgent` Subclasses | Individual agent nodes (Planner, Researcher, Developer, etc.). |
| **Kernel** | `Supervisor` | Registers agents, routes payloads, manages states, and handles interrupts. |
| **System Memory** | `SharedMemory` | Thread-safe, namespace-aware SQLite database with full key-value versioning. |
| **Process Table** | Process State List | Real-time tracking of pid, state (`READY`, `RUNNING`, `COMPLETED`, `FAILED`), and metrics. |
| **Dependency Table** | `DependencyManager` | Directed Acyclic Graph (DAG) mapping prerequisites and upstream/downstream chains. |
| **Process Snapshots** | `CheckpointManager` | In-memory backups of agent states to enable rollbacks on failures. |
| **Selective Rollback** | `RecoveryEngine` | Re-running only the affected downstream agents after a failure without rebooting the system. |

---

## 2. System Architecture & Components

```mermaid
graph TD
    Client[HTTP API / FastAPI] --> Supervisor[Supervisor Kernel]
    Supervisor --> ExecEngine[Execution Engine]
    Supervisor --> DepManager[Dependency Manager]
    Supervisor --> Mem[Shared Memory SQLite]
    Supervisor --> Checkpoint[Checkpoint Manager]
    ExecEngine --> Agents[BaseAgent Implementations]
    Agents --> LLMClient[QwenClient (OpenAI-compatible)]
    Recovery[Recovery Engine] --> DepManager
    Recovery --> Checkpoint
```

### Core Code Map
* **`app/supervisor/`**: Coordinates tasks, registers agents, spawns process states, and controls execution flow.
* **`app/memory/`**: SQLite-backed versioned database. Stores key-value state parameters mapped to namespaces.
* **`app/dependency/`**: Tracks dependencies using a NetworkX DAG model.
* **`app/runtime/`**: Handles synchronous/parallel execution, thread safety, process status transitions, and scheduler queues.
* **`app/checkpoint/`**: Manages snapshots of agent task payloads.
* **`app/agents/`**: Standard AI Agent implementations (Planner, Researcher, Developer, Tester, Reviewer).
* **`app/llm/`**: Core utilities to render templates and route prompts to model clients.
* **`app/api/`**: Exposes FastAPI endpoints for remote runtime administration.
* **`app/static/`**: React-based live dashboard for monitoring.

---

## 3. Complete Module List & Implementation Status

### ✅ Modules 1-9: Core Runtime
1. **Core Infrastructure**: Foundation for the entire runtime system
2. **Supervisor Kernel**: Task coordination and agent management
3. **Shared Memory**: Thread-safe, versioned SQLite key-value store
4. **Dependency Manager**: Directed Acyclic Graph (DAG) for dependencies
5. **Execution Engine**: Thread-pool-based parallel execution
6. **Checkpoint Manager**: Task state snapshots for rollback
7. **Recovery Engine**: Selective rollback and task recovery
8. **Event Bus**: Event-driven architecture for lifecycle events
9. **Agent Framework**: BaseAgent class and agent contracts

### ✅ Module 10: Qwen Cloud Integration
- OpenAI-compatible client (`app/llm/qwen_client.py`)
- Streaming responses (sync and async)
- Retry logic with exponential backoff
- Model selection
- Token usage tracking
- Configuration via environment variables (QWEN_BASE_URL, QWEN_API_KEY, QWEN_MODEL, QWEN_MAX_RETRIES, QWEN_TIMEOUT)

### ✅ Module 11: AI Agents
- 5 Production-ready agents: Planner, Researcher, Developer, Tester, Reviewer
- All inherit from BaseAgent
- Agents communicate via Shared Memory only
- Supervisor coordinates execution

### ✅ Module 12: FastAPI APIs
Endpoints available at http://localhost:8000:
- `/` - Root endpoint
- `/health` - Health check
- `/status` - Full runtime status
- `/agents` - List all agents
- `/agents/{agent_id}` - Get agent details
- `/tasks` (GET) - List all tasks
- `/tasks` (POST) - Submit new task
- `/tasks/{task_id}` - Get task status/result
- `/tasks/{task_id}/run` - Run a task manually
- `/assign` - Quick task assignment
- `/processes` - List all processes
- `/memory` (GET) - Get shared memory contents
- `/memory` (POST) - Write to shared memory
- `/memory/{key}` - Read/delete specific memory key
- `/dependencies` - Get dependency graph
- `/dependencies/visualize` - Interactive dependency visualization
- `/checkpoints` (GET) - List all checkpoints
- `/checkpoints` (POST) - Create new checkpoint
- `/checkpoints/{checkpoint_id}` - Get checkpoint details
- `/rollback` - Rollback to checkpoint
- `/recovery` - Trigger task recovery
- `/events` - List recent events
- `/ws` - WebSocket for real-time updates
- `/dashboard` - Live monitoring dashboard
- `/stream` - SSE stream for real-time updates

### ✅ Module 13: React Dashboard
- Live process table with real-time updates
- Execution graph using React Flow
- Dependency graph visualization
- Checkpoint viewer
- Shared memory viewer
- Events log
- Statistics display (running, completed, failed, total processes)

---

## 4. Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Create a `.env` file in the project root (optional, but recommended):
```env
# Qwen Cloud Configuration
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_API_KEY=your_qwen_api_key_here
QWEN_MODEL=qwen-turbo
QWEN_MAX_RETRIES=3
QWEN_TIMEOUT=60.0

# AgentSphere Configuration
AGENTSPHERE_LOG_LEVEL=INFO
AGENTSPHERE_DB_PATH=./shared_memory.sqlite
AGENTSPHERE_REDIS_URL=
AGENTSPHERE_ENABLE_METRICS=true
```

### Step 3: Run the Application
```powershell
python main.py
```
This boots up the FastAPI backend on `http://localhost:8000`.

### Step 4: Access the Dashboard
Open http://localhost:8000/dashboard in your browser to use the live monitoring dashboard!

---

## 5. Testing

To run the complete test suite:
```powershell
pytest tests/ -v
```

---

## 6. API Documentation

Once the server is running, you can access the auto-generated API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 7. Guidelines for Coding Agents
When editing code in this workspace, you must adhere to the following rules:
1. **Keep Agents Stateless**: Do not rely on local class variables to store execution state across tasks. Rely purely on inputs passed via the Supervisor or read from `SharedMemory`.
2. **Write Deterministic Output**: Ensure outputs are reproducible under identical inputs to allow safe process replays.
3. **Log Explicit Failures**: Never log generic error messages. When executing fails, output clean, structured exception logs so the `Supervisor` can decide the exact scope of selective rollback.
