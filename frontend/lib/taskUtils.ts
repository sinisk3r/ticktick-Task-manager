import { Task } from "@/types/task"

/**
 * Get the effective quadrant for a task, prioritizing manual override > effective > eisenhower
 */
export function getQuadrant(task: Task): string | null | undefined {
  return task.manual_quadrant_override || task.effective_quadrant || task.eisenhower_quadrant
}
