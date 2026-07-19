# AgentSphere OS v4 — Microkernel OS for Autonomous AI Production

AgentSphere OS v4 is a highly resilient, microkernel-based operating system designed to treat autonomous AI agents as managed OS processes. By isolating agent tasks inside secure sandboxes and routing operations through scheduler queues and fault-tolerance recovery lifecycles, AgentSphere OS ensures robust, multi-agent orchestrations.

---

## 🏗️ Architectural Overview

```
                      ┌─────────────────────────────────────────┐
                      │             React Dashboard             │
                      └────────────────────┬────────────────────┘
                                           │ WebSocket/HTTP
                      ┌────────────────────▼────────────────────┐
                      │             FastAPI Gateway             │
                      └────────────────────┬────────────────────┘
                                           │
  ┌────────────────────────────────────────▼────────────────────────────────────────┐
  │                           AgentSphere Microkernel                               │
  ├─────────────────────────────────────────────────────────────────────────────────┤
  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐  │
  │  │  Supervisor  │   │  Scheduler   │   │  Event Bus   │   │ Resource Monitor │  │
  │  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────────┘  │
  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐  │
  │  │ Model Router │   │ CheckpointMgr│   │RecoveryEngine│   │  Plugin Manager  │  │
  │  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────────┘  │
  └────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
  ┌────────────────────────────────────────▼────────────────────────────────────────┐
  │                            Data & Storage Engines                               │
  ├─────────────────────────────────────────────────────────────────────────────────┤
  │   ┌──────────────┐       ┌───────────────┐       ┌──────────────┐               │
  │   │ SQLite State │       │ Qdrant Vector │       │  Redis Cache │               │
  │   │ (Checkpoints)│       │ (Semantic Mem)│       │  (Sessions)  │               │
  │   └──────────────┘       └───────────────┘       └──────────────┘               │
  └─────────────────────────────────────────────────────────────────────────────────┘
```

- **Process Isolation (Sandbox)**: Executes custom python scripts in isolated sandboxed contexts with thread-local trace-based timeouts (`sys.settrace`) preventing thread lockups.
- **Fault-Tolerant Recovery**: Checkpoints database states at each stage. When a failure is detected, the Recovery Engine executes a downstream graph walk, rolls back the environment to the last successful checkpoint, and restarts only the failed process node.
- **Intelligent Model Router**: Dynamically selects the appropriate Qwen LLM endpoint model, supports priority fallbacks, and tracks API cost budgets in real time.
- **Resource Monitor**: Constantly samples CPU, RAM, and Disk footprints, automatically suspending runaway processes.

---

## ⚡ Quick Start (Local Run)

### 1. Install Dependencies
Ensure you have Python 3.13 installed:
```bash
python -m pip install -r requirements.txt
```

### 2. Configure Qwen API Credentials
Create a `.env` file in the root directory (or use the **Settings** tab in the dashboard UI):
```env
QWEN_API_KEY=your-sk-api-key-here
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max
```

### 3. Start the Server
Launch the FastAPI microkernel instance:
```bash
python main.py
```
Open **[http://localhost:8000/dashboard](http://localhost:8000/dashboard)** in your browser to access the control center.

### 4. Run Test Assertions
Execute the full test suite verifying microkernel functionality:
```bash
python -m pytest
```

---

## 🐳 Production Deployment (Docker Compose)

The system is configured to run inside containerized clusters isolating routing, cached data layers, and vector storage.

Launch the full cluster (FastAPI app, Nginx gateway, Redis, Qdrant):
```bash
docker-compose up --build
```
This boots:
* **Nginx Gateway (Port 80)**: Routes reverse proxies to the backend and upgrades WS channels.
* **FastAPI Microkernel (Exposed internally on 8000)**: Serves endpoints and event buffers.
* **Redis Cache (Port 6379)**: Manages concurrent cache lock states.
* **Qdrant DB (Port 6333)**: Indexes semantic embeddings.

---

## 🎬 Final Demo Scenario: Fault-Tolerant AI Showrunner Pipeline

The primary end-to-end hackathon demonstration flow showcases the core resiliency value of the microkernel design:

1. **Task Submission**: A user enters a prompt: `"Create a 2-minute animated advertisement."`
2. **Decomposition**: The Supervisor instantiates a process PID and lays out the task execution graph:
   ```
   Planner ➔ Writer ➔ Storyboard ➔ Video Agent (Wan) ➔ Voice Agent ➔ Editor
   ```
3. **Checkpoint Rollback Trigger**:
   - The execution runs successfully through Planner, Writer, and Storyboard.
   - During the **Video Agent** stage, we simulate an unexpected API exception (raising a FAILED process state).
   - Instead of losing progress and restarting from scratch, the **Recovery Engine** reads the DAG, retrieves the checkpoint immediately prior to the video stage, restores the environment, and restarts **only** the Video Agent.
4. **Assembly**: The video compiles successfully, saving assets to **Alibaba OSS**, and the results render on the React Dashboard.
