export interface Task {
  id: number
  title: string
  description?: string
  status: string
  due_date?: string | null
  start_date?: string | null
  ticktick_priority?: number
  project_name?: string
  ticktick_tags?: string[]
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
  ticktick_task_id?: string
}

export interface TasksResponse {
  tasks: Task[]
  total: number
}
