export interface ApiTraining {
  id: number
  live_type: '带货' | '娱乐互动' | '知识内容'
  goal: string
  topic: string | null
  product_info: string | null
  script: string | null
  status: 'created' | 'recording' | 'saved' | 'analyzing' | 'feedback_ready' | 'failed'
  prev_training_id: number | null
  selected_must_cover_scenario_ids: string[]
  created_at: string | null
  finished_at: string | null
}

export interface ScriptBullet {
  at_sec: number
  kind: string
  text: string
  scenario_id?: string | null
  viewer_intent?: string | null
  sample_type?: string | null
  difficulty?: number | null
  must_cover?: string[]
  failure_signals?: string[]
  source_refs?: string[]
}

export interface ApiIssue {
  dimension: string
  start_sec: number
  end_sec: number
  evidence: string
  problem: string
  suggestion: string
  retrain_target: string
  trigger_bullet?: string | null
  scenario_id?: string | null
  rule_ids?: string[]
  missed_points?: string[]
  source_refs?: string[]
}

export interface FeedbackResponse {
  status: ApiTraining['status']
  feedback: {
    issues: ApiIssue[]
    top_issue_ids: number[]
  } | null
}

export interface TrainingSide {
  training: ApiTraining
  issues: ApiIssue[]
  top_issue_ids: number[]
}

export interface CompareResponse {
  current: TrainingSide
  previous: TrainingSide
}

export interface CreateTrainingInput {
  live_type: ApiTraining['live_type']
  goal: string
  topic?: string | null
  product_info?: string | null
  script?: string | null
}

export interface CreateTrainingResponse {
  training: ApiTraining
  script: ScriptBullet[]
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: 'application/json',
      ...init?.headers,
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const message = body?.error?.message ?? body?.detail ?? `请求失败（${response.status}）`
    throw new Error(typeof message === 'string' ? message : '请求失败，请稍后重试')
  }
  return response.json() as Promise<T>
}

export function createTraining(input: CreateTrainingInput): Promise<CreateTrainingResponse> {
  return request('/api/v1/trainings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export async function getTraining(id: number): Promise<ApiTraining> {
  const data = await request<{ training: ApiTraining }>(`/api/v1/trainings/${id}`)
  return data.training
}

export function getFeedback(id: number): Promise<FeedbackResponse> {
  return request(`/api/v1/trainings/${id}/feedback`)
}

export async function finishTraining(
  id: number,
  recording: Blob,
  durationSec: number,
): Promise<ApiTraining> {
  const form = new FormData()
  form.append('file', recording, 'recording.webm')
  form.append('bullets', '[]')
  form.append('duration_sec', String(durationSec))
  const data = await request<{ training: ApiTraining }>(`/api/v1/trainings/${id}/finish`, {
    method: 'POST',
    body: form,
  })
  return data.training
}

export function retryTraining(id: number): Promise<{ training: ApiTraining }> {
  return request(`/api/v1/trainings/${id}/retry`, { method: 'POST' })
}

export function retrain(id: number): Promise<CreateTrainingResponse> {
  return request(`/api/v1/trainings/${id}/retrain`, { method: 'POST' })
}

export function getComparison(id: number): Promise<CompareResponse> {
  return request(`/api/v1/trainings/${id}/compare`)
}

export function recordingUrl(id: number): string {
  return apiUrl(`/api/v1/trainings/${id}/recording`)
}

export function trainingSocketUrl(id: number): string {
  const configured = import.meta.env.VITE_WS_BASE_URL?.replace(/\/$/, '')
  if (configured) return `${configured}/api/v1/trainings/${id}/asr/ws`
  const url = new URL(`/api/v1/trainings/${id}/asr/ws`, window.location.origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}

const scriptKey = (id: number) => `ai-live-coach:training-script:${id}`

export function saveTrainingScript(id: number, script: ScriptBullet[]): void {
  sessionStorage.setItem(scriptKey(id), JSON.stringify(script))
}

export function loadTrainingScript(id: number): ScriptBullet[] {
  try {
    return JSON.parse(sessionStorage.getItem(scriptKey(id)) ?? '[]') as ScriptBullet[]
  } catch {
    return []
  }
}
