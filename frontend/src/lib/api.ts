/// <reference types="vite/client" />
/** Typed API client for the FastAPI backend. */

const BASE = import.meta.env.VITE_API_URL ?? ''

async function req<T>(
  method: string,
  path: string,
  body?: unknown,
  headers?: Record<string, string>,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...headers },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText)
    throw new Error(`${method} ${path} → ${res.status}: ${msg}`)
  }
  return res.json() as Promise<T>
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ProviderInfo {
  id: string
  name: string
  needs_key: boolean
  needs_base_url: boolean
  default_base_url: string
  key_env: string | null
  description: string
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  context_length: number | null
}

export interface DatasetInfo {
  name: string
  count: number | null
  size_bytes: number
}

export interface DatasetPreview {
  name: string
  count: number
  preview: Record<string, unknown>[]
}

export interface JobSummary {
  id: string
  status: string
  created_at: string
  started_at: string | null
  completed_at: string | null
  result_path: string | null
  error: string | null
  goal_count: number | null
  dataset: string
  // Enriched fields
  target_model?: string
  attack_model?: string
  judge_model?: string
  attacks?: string[]
  defenses?: string[]
  name?: string
  queue_position?: number | null
  duration_seconds?: number | null
  progress?: { current: number; total: number; pct: number; label: string } | null
  log_tail?: string[]
}

export interface LeaderRow {
  target_model: string
  attack_name: string
  defense_name: string
  attack_model: string
  judge_model: string
  source_files: string[]
  total_experiments: number
  MIR: number
  Task_Success: number
  TIR: number
  DBR: number
  QTJ: number | null
  avg_duration: number
  avg_queries: number
  total_tool_calls: number
  avg_correct_tool_calls: number
  avg_wrong_tool_calls: number
  avg_harmful_tool_calls: number
  n_malicious: number
}

export type LeaderboardGroupBy = 'combo' | 'model' | 'attack'

export interface LeaderboardResponse {
  rows: LeaderRow[]
  total: number
  limit: number
  offset: number
  has_more: boolean
  group_by: LeaderboardGroupBy
  sort_key: keyof LeaderRow | string
  sort_dir: 'asc' | 'desc'
}

export interface DatasetScope {
  mode: 'full' | 'single' | 'range' | 'sample'
  index?: number
  start?: number
  end?: number
  n?: number
  seed?: number
}

export interface ProviderCredential {
  provider_id: string
  api_key?: string
  base_url?: string
}

export interface AttackSpec {
  name: string
  params?: Record<string, unknown>
}

export interface LaunchRequest {
  target_provider: string
  target_model: string
  attack_provider?: string
  attack_model?: string
  judge_provider?: string
  judge_model?: string
  dataset: string
  dataset_scope?: DatasetScope
  attacks?: (string | AttackSpec)[]
  defenses?: string[]
  defense_params?: Record<string, Record<string, unknown>>
  wandb_enabled?: boolean
  wandb_project?: string
  wandb_entity?: string
  wandb_run_name?: string
  calls_per_minute?: number
  credentials?: ProviderCredential[]
  extra?: Record<string, unknown>
}

// ── Provider APIs ─────────────────────────────────────────────────────────────

export const api = {
  getProviders: () => req<ProviderInfo[]>('GET', '/api/providers'),

  validateProvider: (id: string, api_key: string, base_url?: string) =>
    req<{ valid: boolean }>('POST', `/api/providers/${id}/validate`, { api_key, base_url }),

  listModels: (id: string, api_key: string, base_url?: string) =>
    req<ModelInfo[]>('GET', `/api/providers/${id}/models?api_key=${encodeURIComponent(api_key)}&base_url=${encodeURIComponent(base_url ?? '')}`),

  pullOllamaModel: (model: string, base_url?: string) =>
    req<{ accepted: boolean }>('POST', '/api/providers/ollama/pull', { model, base_url }),

  // ── Datasets ──────────────────────────────────────────────────────────────

  listDatasets: () => req<DatasetInfo[]>('GET', '/api/datasets'),

  previewDataset: (name: string, limit = 5) =>
    req<DatasetPreview>('GET', `/api/datasets/${encodeURIComponent(name)}?limit=${limit}`),

  getEntry: (name: string, index: number) =>
    req<{ index: number; entry: Record<string, unknown> }>(
      'GET',
      `/api/datasets/${encodeURIComponent(name)}/sample/${index}`,
    ),

  uploadDataset: async (file: File, name?: string): Promise<DatasetInfo> => {
    const form = new FormData()
    form.append('file', file)
    if (name) form.append('name', name)
    const res = await fetch(`${BASE}/api/datasets/upload`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  deleteDataset: (name: string) =>
    req<{ deleted: string }>('DELETE', `/api/datasets/${encodeURIComponent(name)}`),

  // ── Eval ──────────────────────────────────────────────────────────────────

  launchEval: (payload: LaunchRequest) =>
    req<JobSummary>('POST', '/api/eval/launch', payload),

  listJobs: () => req<JobSummary[]>('GET', '/api/eval/jobs'),

  getJob: (id: string) => req<JobSummary & { log_tail: string[] }>('GET', `/api/eval/${id}`),

  cancelJob: (id: string) => req<{ cancelled: boolean }>('DELETE', `/api/eval/${id}`),
  removeJob: (id: string) => req<{ removed: boolean } | { cancelled: boolean }>('DELETE', `/api/eval/${id}`),

  getJobResults: (id: string) => req<unknown>('GET', `/api/eval/${id}/results`),

  // ── Results ───────────────────────────────────────────────────────────────

  listResults: () =>
    req<{ path: string; size_bytes: number; modified: number }[]>('GET', '/api/results'),

  getResultsSummary: () =>
    req<{
      path: string; size_bytes: number; modified: number
      target_model: string; attack_name: string; attack_model: string
      judge_model: string; defense_name: string
      record_count: number; succeeded: number; MIR: number
    }[]>('GET', '/api/results/summary'),

  getResult: (relPath: string) =>
    req<unknown>('GET', `/api/results/${encodeURIComponent(relPath)}`),

  deleteResult: (relPath: string) =>
    req<{ deleted: string }>('DELETE', `/api/results/${encodeURIComponent(relPath)}`),

  getLeaderboard: (params?: {
    groupBy?: LeaderboardGroupBy
    limit?: number
    offset?: number
    sortKey?: keyof LeaderRow
    sortDir?: 'asc' | 'desc'
    filterModel?: string
    filterAttack?: string
    filterDefense?: string
  }): Promise<LeaderRow[] | LeaderboardResponse> => {
    const q = new URLSearchParams()
    if (params?.groupBy) q.set('group_by', params.groupBy)
    if (params?.limit !== undefined) q.set('limit', String(params.limit))
    if (params?.offset !== undefined) q.set('offset', String(params.offset))
    if (params?.sortKey) q.set('sort_key', String(params.sortKey))
    if (params?.sortDir) q.set('sort_dir', params.sortDir)
    if (params?.filterModel) q.set('filter_target_model', params.filterModel)
    if (params?.filterAttack) q.set('filter_attack_name', params.filterAttack)
    if (params?.filterDefense) q.set('filter_defense_name', params.filterDefense)
    const suffix = q.toString()
    return req<LeaderboardResponse>('GET', `/api/results/leaderboard${suffix ? `?${suffix}` : ''}`).then((res) => {
      // Backwards compatibility: callers that invoked getLeaderboard() without params
      // expect an array. If no params were supplied, return the `rows` array directly.
      if (!params) return res.rows
      return res
    })
  },
}

// ── WebSocket helpers ─────────────────────────────────────────────────────────

export function createJobSocket(
  jobId: string,
  onLog: (line: string) => void,
  onDone: (status: string) => void,
): WebSocket {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const host = BASE ? new URL(BASE).host : location.host
  const ws = new WebSocket(`${protocol}://${host}/api/eval/${jobId}/stream`)

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data) as { type: string; line?: string; status?: string }
      if (msg.type === 'log' && msg.line !== undefined) onLog(msg.line)
      else if (msg.type === 'done') onDone(msg.status ?? 'unknown')
    } catch (_) { }
  }
  return ws
}
