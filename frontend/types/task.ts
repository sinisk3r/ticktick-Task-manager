export interface Task {
  id: number
  title: string
  description?: string
  status: string
  due_date?: string | null
  start_date?: string | null
  reminder_time?: string | null
  repeat_flag?: string | null
  all_day?: boolean
  ticktick_priority?: number
  project_id?: number | null
  project_name?: string
  ticktick_project_id?: string
  ticktick_tags?: string[]
  time_estimate?: number | null
  focus_time?: number | null
  urgency_score?: number
  importance_score?: number
  eisenhower_quadrant?: string
  effective_quadrant?: string
  manual_quadrant_override?: string
  manual_override_reason?: string
  manual_override_at?: string
  manual_order?: number
  analysis_reasoning?: string
  created_at?: string
  updated_at?: string
  analyzed_at?: string
  ticktick_task_id?: string
}

export interface TasksResponse {
  tasks: Task[]
  total: number
}

export interface Suggestion {
  id: number
  type: string
  current: any
  suggested: any
  reason: string
  confidence: number
}

export interface SuggestionsResponse {
  suggestions: Suggestion[]
}
