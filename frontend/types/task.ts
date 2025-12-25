export interface Task {
  id: number
  title: string
  description?: string
  status: string
  due_date?: string | null
  start_date?: string | null
  reminder_time?: string | null  // Deprecated - use reminders array instead
  reminders?: number[]
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
  parent_task_id?: string | null  // TickTick parent ID
  parent_task_id_int?: number | null  // Internal parent task ID
  subtasks?: Task[]  // Optional - populated when fetching with include_subtasks
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

export interface TaskSummary {
  total: number
  total_active: number
  total_completed: number
  total_deleted: number
  quadrants: Record<string, number>
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

// Enhance endpoint types
export interface EnhanceRequest {
  enhance_description?: boolean
  enhance_dates?: boolean
  enhance_project?: boolean
  enhance_time?: boolean
}

export interface EnhancedSuggestion {
  type: string
  current: any
  suggested: any
  current_display?: string
  suggested_display: string
  reason: string
  confidence: number
  priority: 'high' | 'medium' | 'low'
}

export interface EnhanceResponse {
  // NEW: Multi-suggestion with confidence
  suggestions?: EnhancedSuggestion[]
  analysis?: {
    urgency_score: number
    importance_score: number
    eisenhower_quadrant: string
    effort_hours: number
  }
  // Legacy fields (backward compatibility)
  suggested_description?: string | null
  suggested_due?: string | null
  suggested_start?: string | null
  suggested_reminder?: string | null
  suggested_project?: {
    name?: string
    label?: string
    id?: number
    ticktick_project_id?: string | null
  } | null
  suggested_tags?: string[] | null
  suggested_time_estimate?: number | null
  rationale?: string | null
  raw_suggestions?: Array<{
    type: string
    current?: any
    suggested?: any
    reason?: string
    confidence?: number
  }>
}
