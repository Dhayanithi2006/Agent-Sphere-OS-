// API client for AgentSphere OS backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchAPI(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  getStatus: () => fetchAPI('/status'),
  getAgents: () => fetchAPI('/agents'),
  getProcesses: () => fetchAPI('/processes'),
  getTasks: () => fetchAPI('/tasks'),
  getMemory: () => fetchAPI('/memory'),
  getMemoryKey: (key: string, namespace: string) =>
    fetchAPI(`/memory/${key}?namespace=${namespace}`),
  writeMemory: (namespace: string, key: string, value: unknown) =>
    fetchAPI('/memory', {
      method: 'POST',
      body: JSON.stringify({ namespace, key, value }),
    }),
  getCheckpoints: (limit = 50) => fetchAPI(`/checkpoints?limit=${limit}`),
  getEvents: () => fetchAPI('/events'),
  getDependencies: () => fetchAPI('/dependencies'),
  getDiagnostics: () => fetchAPI('/diagnostics'),
  getSupervisor: () => fetchAPI('/supervisor'),
  getMetrics: () => fetchAPI('/api/metrics'),
  getAssets: () => fetchAPI('/api/assets'),
  getBenchmarks: () => fetchAPI('/api/benchmarks'),
  getShowrunnerStatus: () => fetchAPI('/api/showrunner/status'),
  getMarketplace: () => fetchAPI('/api/marketplace'),
  getDashboard: () => fetchAPI('/dashboard'),

  execute: (task: string, workflow?: string) =>
    fetchAPI('/kernel/execute', {
      method: 'POST',
      body: JSON.stringify({ task, workflow: workflow || 'coding' }),
    }),

  assignTask: (agentId: string, task: string) =>
    fetchAPI('/assign', {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId, task }),
    }),

  recover: (taskId: string) =>
    fetchAPI(`/recovery?task_id=${taskId}`, { method: 'POST' }),

  rollback: (checkpointId: string) =>
    fetchAPI(`/rollback/${checkpointId}`, { method: 'POST' }),

  approveShowrunner: () =>
    fetchAPI('/api/showrunner/approve', { method: 'POST' }),

  rejectShowrunner: () =>
    fetchAPI('/api/showrunner/reject', { method: 'POST' }),

  startShowrunner: (goal: string, mediaType: string, user = 'User') =>
    fetchAPI('/api/showrunner/generate', {
      method: 'POST',
      body: JSON.stringify({ movie_goal: goal, type: mediaType, user }),
    }),
};

export default api;
