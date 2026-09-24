export interface ApiTraining {
  id: number
  live_type: '带货' | '娱乐互动' | '知识内容'
  goal: string
  topic: string | null
  product_info: string | null
  script: string | null
  status: 'created' | 'recording' | 'saved' | 'analyzing' | 'feedback_ready' | 'failed'
  prev_training_id: number | null
  practice_mode: 'focus' | 'full'
  media_kind: 'video' | 'audio' | 'none'
  selected_must_cover_scenario_ids: string[]
  created_at: string | null
  finished_at: string | null
  media?: ApiMedia | null
}

export interface ApiMedia {
  exists: boolean
  media_kind: 'video' | 'audio' | 'none'
  mime_type: string | null
  duration_sec: number | null
  size_bytes: number | null
}

export interface ApiRecording {
  recording_id: number
  training_id: number
  goal: string
  live_type: string
  practice_mode: string
  media_kind: string
  mime_type: string | null
  duration_sec: number | null
  size_bytes: number | null
  exists: boolean
  created_at: string | null
}

export interface WeekStats {
  timezone: string
  week: {
    training_count: number
    total_duration_sec: number
    required_response_bullets: number
    responded_bullets: number
    timely_responded_bullets: number
    response_rate: number | null
    avg_response_sec: number | null
    sample_sufficient: boolean
    sample_count: number
  }
  previous_week: {
    training_count: number
    total_duration_sec: number
    required_response_bullets: number
    responded_bullets: number
    timely_responded_bullets: number
    response_rate: number | null
    avg_response_sec: number | null
    sample_sufficient: boolean
    sample_count: number
  }
  change: {
    training_count_delta?: number
    response_rate_delta?: number
  }
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
  practice_mode?: 'focus' | 'full'
  media_kind?: 'video' | 'audio' | 'none'
}

export interface CreateTrainingResponse {
  training: ApiTraining
  script: ScriptBullet[]
}

export interface TutorialStep {
  title: string
  detail: string
}

export interface ApiTutorial {
  id: string
  title: string
  category: string
  durationMin: number
  level: string
  description: string
  tags: string[]
  objective: string
  whenToUse: string[]
  steps: TutorialStep[]
  badExample: string
  goodExample: string
  mistakes: string[]
  checklist: string[]
  practiceTopic: string
  ruleRefs: string[]
  reviewStatus: 'pending_teacher_review'
}

export interface TutorialProgressSummary {
  completed_ids: string[]
  completed_count: number
  total: number
}

export interface TutorialCatalogResponse {
  tutorials: ApiTutorial[]
  progress: TutorialProgressSummary
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

export async function getTrainingMedia(id: number): Promise<ApiMedia> {
  return request<ApiMedia>(`/api/v1/trainings/${id}/media`)
}

export function listTrainings(): Promise<ApiTraining[]> {
  return request<{ trainings: ApiTraining[] }>('/api/v1/trainings').then((d) => d.trainings)
}

export function listRecordings(): Promise<ApiRecording[]> {
  return request<{ recordings: ApiRecording[] }>('/api/v1/recordings').then((d) => d.recordings)
}

export function getWeekStats(): Promise<WeekStats> {
  return request<WeekStats>('/api/v1/stats/week')
}

export function getTutorials(): Promise<TutorialCatalogResponse> {
  return request('/api/v1/tutorials')
}

export function getTutorial(id: string): Promise<{ tutorial: ApiTutorial; completed: boolean }> {
  return request(`/api/v1/tutorials/${encodeURIComponent(id)}`)
}

export function updateTutorialProgress(id: string, completed: boolean): Promise<{
  progress: { tutorial_id: string; completed: boolean; completed_at: string | null }
  summary: TutorialProgressSummary
}> {
  return request(`/api/v1/tutorials/${encodeURIComponent(id)}/progress`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ completed }),
  })
}

export function getTutorialRecommendations(trainingId: number): Promise<ApiTutorial[]> {
  return request<{ tutorials: ApiTutorial[] }>(`/api/v1/tutorials/recommendations/${trainingId}`)
    .then((data) => data.tutorials)
}

export function deleteTraining(id: number): Promise<{ deleted: boolean }> {
  return request(`/api/v1/trainings/${id}`, { method: 'DELETE' })
}

export function getFeedback(id: number): Promise<FeedbackResponse> {
  return request(`/api/v1/trainings/${id}/feedback`)
}

export async function finishTraining(
  id: number,
  recording: Blob,
  durationSec: number,
  mediaKind: 'video' | 'audio' | 'none' = 'video',
): Promise<ApiTraining> {
  const form = new FormData()
  form.append('file', recording, mediaKind === 'audio' ? 'recording.webm' : 'recording.webm')
  form.append('bullets', '[]')
  form.append('duration_sec', String(durationSec))
  form.append('media_kind', mediaKind)
  if (mediaKind === 'audio') form.append('mime_type', recording.type || 'audio/webm')
  else form.append('mime_type', recording.type || 'video/webm')
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
