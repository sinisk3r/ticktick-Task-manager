"use client"

import { useEffect, useMemo, useState, type DragEvent } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Progress } from "@/components/ui/progress"
import { api } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, ChevronDown, ChevronUp, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Task {
  id: number
  title: string
  description?: string
  urgency_score: number
  importance_score: number
  eisenhower_quadrant: string
  effective_quadrant?: string
  analysis_reasoning?: string
  manual_quadrant_override?: string
  manual_override_reason?: string
  manual_override_at?: string
  manual_order?: number
  status: string
  created_at: string
  ticktick_task_id?: string
}

interface TasksResponse {
  tasks: Task[]
  total: number
}

interface EisenhowerMatrixProps {
  tasks?: Task[]
  onTasksUpdate?: (tasks: Task[]) => void
  refresh?: () => Promise<void>
}

const QuadrantCard = ({
  title,
  description,
  tasks,
  bgColor,
  borderColor,
  icon,
  onDrop,
  onResetTask,
  onDragStartTask,
  onDropTask,
}: {
  title: string
  description: string
  tasks: Task[]
  bgColor: string
  borderColor: string
  icon: string
  onDrop: (event: DragEvent) => void
  onResetTask?: (taskId: number) => Promise<void>
  onDragStartTask?: (taskId: number) => (event: DragEvent) => void
  onDropTask?: (taskId: number) => (event: DragEvent) => void
}) => {
  return (
    <Card
      className={`p-6 ${bgColor} ${borderColor} border-2 h-full min-h-[300px] flex flex-col`}
      onDragOver={(e) => e.preventDefault()}
      onDrop={onDrop}
    >
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">{icon}</span>
          <h3 className="text-lg font-bold text-foreground">{title}</h3>
        </div>
        <p className="text-xs text-muted-foreground">{description}</p>
        <Badge variant="secondary" className="mt-2">
          {tasks.length} {tasks.length === 1 ? "task" : "tasks"}
        </Badge>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto max-h-[400px]">
        {tasks.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            No tasks in this quadrant
          </p>
        ) : (
          tasks.map((task) => (
            <TaskPopover
              key={task.id}
              task={task}
              onReset={onResetTask ? () => onResetTask(task.id) : undefined}
              onDragStart={onDragStartTask ? onDragStartTask(task.id) : undefined}
              onDrop={onDropTask ? onDropTask(task.id) : undefined}
            />
          ))
        )}
      </div>
    </Card>
  )
}

const TaskPopover = ({
  task,
  onReset,
  onDragStart,
  onDrop,
}: {
  task: Task
  onReset?: () => Promise<void>
  onDragStart?: (event: DragEvent) => void
  onDrop?: (event: DragEvent) => void
}) => {
  const [expanded, setExpanded] = useState(false)

  const truncatedReasoning = task.analysis_reasoning
    ? task.analysis_reasoning.length > 120
      ? task.analysis_reasoning.substring(0, 120) + "..."
      : task.analysis_reasoning
    : "No AI analysis available"

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className="w-full text-left p-3 rounded-lg bg-background border border-border hover:bg-accent transition-colors"
          draggable
          onDragStart={onDragStart}
          onDragOver={(e) => {
            e.preventDefault()
            e.stopPropagation()
          }}
          onDrop={onDrop}
        >
          <p className="text-sm font-medium text-foreground truncate">
            {task.title}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-muted-foreground">U: {task.urgency_score}</span>
            <span className="text-xs text-muted-foreground">I: {task.importance_score}</span>
          </div>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-96 bg-popover border-border" side="right">
        <div className="space-y-3">
          <h4 className="font-semibold text-gray-100 leading-tight">
            {task.title}
          </h4>

          {task.description && (
            <p className="text-sm text-gray-300">
              {task.description.length > 150
                ? task.description.substring(0, 150) + "..."
                : task.description}
            </p>
          )}

          {/* Urgency Score */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-gray-400">Urgency</span>
              <span className="text-xs font-semibold text-gray-300">
                {task.urgency_score}/10
              </span>
            </div>
            <Progress value={task.urgency_score * 10} className="h-2" />
          </div>

          {/* Importance Score */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-gray-400">Importance</span>
              <span className="text-xs font-semibold text-gray-300">
                {task.importance_score}/10
              </span>
            </div>
            <Progress value={task.importance_score * 10} className="h-2" />
          </div>

          {/* AI Reasoning */}
          <div className="border-t border-gray-700 pt-3">
            <div className="flex items-start gap-2">
              <span className="text-base">💡</span>
              <div className="flex-1">
                <p className="text-xs text-gray-300 leading-relaxed">
                  {expanded ? task.analysis_reasoning : truncatedReasoning}
                </p>
              </div>
            </div>

            {task.analysis_reasoning && task.analysis_reasoning.length > 120 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setExpanded(!expanded)}
                className="w-full mt-2 text-xs text-gray-400 hover:text-gray-200"
              >
                {expanded ? (
                  <>
                    <ChevronUp className="h-3 w-3 mr-1" />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3 mr-1" />
                    Read more
                  </>
                )}
              </Button>
            )}
          </div>

          {/* Metadata */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-700">
            <span className="text-xs text-gray-500">
              {new Date(task.created_at).toLocaleDateString()}
            </span>
            {task.manual_quadrant_override && (
              <Badge variant="outline" className="text-[10px]">
                Manual override
              </Badge>
            )}
            {task.ticktick_task_id && (
              <Badge variant="outline" className="text-xs">
                TickTick
              </Badge>
            )}
          </div>

          {task.manual_quadrant_override && (
            <div className="mt-3 flex items-center justify-between border-t border-gray-700 pt-3">
              <div className="text-xs text-gray-400">
                Override: {task.manual_quadrant_override}
                {task.manual_override_reason ? ` — ${task.manual_override_reason}` : ""}
              </div>
              {onReset && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs text-gray-300 hover:text-gray-50"
                  onClick={onReset}
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  Reset
                </Button>
              )}
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}

export function EisenhowerMatrix({ tasks, onTasksUpdate, refresh }: EisenhowerMatrixProps) {
  const controlled = Boolean(tasks && onTasksUpdate)
  const [tasksState, setTasksState] = useState<Task[]>(tasks ?? [])
  const [loading, setLoading] = useState(!controlled)
  const [error, setError] = useState<string | null>(null)
  const [savingTaskId, setSavingTaskId] = useState<number | null>(null)

  const getQuadrant = (task: Task) =>
    task.manual_quadrant_override || task.effective_quadrant || task.eisenhower_quadrant

  const reorderQuadrant = async (quadrant: string, orderedIds: number[]) => {
    try {
      const response = await api.post<TasksResponse>("/api/tasks/reorder", {
        user_id: 1,
        quadrant,
        task_ids: orderedIds,
      })

      // Update state with the response to ensure consistency
      if (response.tasks) {
        const updatedTasks = tasksState.map((t) => {
          const updated = response.tasks.find((rt) => rt.id === t.id)
          return updated ? { ...t, ...updated } : t
        })
        setAndPropagate(updatedTasks)
      }
    } catch (err: any) {
      console.error("Failed to reorder tasks:", err)
      setError(err.message || "Failed to reorder tasks")
      // Refetch to restore correct state
      if (!controlled) {
        await fetchTasks()
      }
      throw err // Re-throw so caller knows it failed
    }
  }

  const setAndPropagate = (next: Task[]) => {
    setTasksState(next)
    if (onTasksUpdate) {
      onTasksUpdate(next)
    }
  }

  const fetchTasks = async () => {
    if (controlled) return
    try {
      setError(null)
      const params = new URLSearchParams({
        user_id: "1",
        status: "active",
        limit: "100",
      })

      const response = await api.get<TasksResponse>(`/api/tasks?${params.toString()}`)

      setAndPropagate(response.tasks || [])
    } catch (err: any) {
      console.error("Failed to fetch tasks:", err)
      setError(err.message || "Failed to load tasks")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (controlled && tasks) {
      setTasksState(tasks)
      setLoading(false)
      return
    }
    fetchTasks()
  }, [controlled, tasks])

  const mergeTask = (updated: Task) => {
    const exists = tasksState.some((t) => t.id === updated.id)
    const next = exists
      ? tasksState.map((t) => (t.id === updated.id ? { ...t, ...updated } : t))
      : [...tasksState, updated]
    setAndPropagate(next)
  }

  const handleQuadrantChange = async (taskId: number, targetQuadrant: string) => {
    setSavingTaskId(taskId)
    setError(null)
    try {
      const updated = await api.patch<Task>(`/api/tasks/${taskId}/quadrant`, {
        manual_quadrant: targetQuadrant,
        reason: "Moved in matrix view",
        source: "matrix",
      })
      mergeTask(updated)
    } catch (err: any) {
      console.error("Failed to update quadrant:", err)
      setError(err.message || "Failed to update task quadrant")
    } finally {
      setSavingTaskId(null)
    }
  }

  const handleReset = async (taskId: number) => {
    setSavingTaskId(taskId)
    setError(null)
    try {
      const updated = await api.patch<Task>(`/api/tasks/${taskId}/quadrant`, {
        reset_to_ai: true,
      })
      mergeTask(updated)
    } catch (err: any) {
      setError(err.message || "Failed to reset override")
    } finally {
      setSavingTaskId(null)
    }
  }

  const handleDrop = (quadrant: string) => async (event: DragEvent) => {
    event.preventDefault()
    const taskId = Number(event.dataTransfer.getData("task-id"))
    if (!taskId) return
    const task = tasksState.find((t) => t.id === taskId)
    if (!task) return
    const currentQuadrant = getQuadrant(task)
    if (currentQuadrant === quadrant) return
    await handleQuadrantChange(taskId, quadrant)
  }

  const onDragStart = (taskId: number) => (event: DragEvent) => {
    event.stopPropagation()
    event.dataTransfer.setData("task-id", String(taskId))
    event.dataTransfer.effectAllowed = "move"
  }

  const handleDropOnTask = (quadrant: string, targetTaskId: number) => async (event: DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    const taskId = Number(event.dataTransfer.getData("task-id"))
    if (!taskId || taskId === targetTaskId) return

    const task = tasksState.find((t) => t.id === taskId)
    if (!task) return

    const currentQuadrant = getQuadrant(task)

    // Build the new order for the target quadrant
    // Start with current bucket, but if task is moving from another quadrant, we need to add it
    let bucket = [...(quadrantBuckets[quadrant as keyof typeof quadrantBuckets] || [])]

    // If moving across quadrants, add the task to the bucket (it won't be there yet)
    if (currentQuadrant !== quadrant) {
      bucket = [...bucket, { ...task, manual_quadrant_override: quadrant }]
    }

    // Remove the dragged task from its current position
    const withoutDragged = bucket.filter((t) => t.id !== taskId)

    // Find where to insert it (before the target task)
    const targetIndex = withoutDragged.findIndex((t) => t.id === targetTaskId)
    if (targetIndex === -1) return

    // Insert the task at the target position
    withoutDragged.splice(targetIndex, 0, { ...task, manual_quadrant_override: quadrant })

    // Update local state optimistically
    const newState = tasksState.map((t) => {
      if (t.id === taskId) {
        return { ...t, manual_quadrant_override: quadrant }
      }
      return t
    })
    setAndPropagate(newState)

    try {
      // If moving across quadrants, update quadrant first
      if (currentQuadrant !== quadrant) {
        await handleQuadrantChange(taskId, quadrant)
      }

      // Then persist the new order for the target quadrant
      await reorderQuadrant(quadrant, withoutDragged.map((t) => t.id))
    } catch (err) {
      // On error, refetch to restore correct state
      if (!controlled) {
        await fetchTasks()
      }
    }
  }

  const quadrantBuckets = useMemo(() => {
    const buckets: Record<string, Task[]> = { Q1: [], Q2: [], Q3: [], Q4: [] }
    tasksState.forEach((task) => {
      const q = getQuadrant(task)
      if (q && buckets[q as keyof typeof buckets]) {
        buckets[q as keyof typeof buckets].push(task)
      }
    })
    // Sort each bucket by manual_order (null values at end), then created_at
    Object.keys(buckets).forEach((key) => {
      buckets[key].sort((a, b) => {
        const aOrder = a.manual_order ?? 999999
        const bOrder = b.manual_order ?? 999999
        if (aOrder !== bOrder) return aOrder - bOrder
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      })
    })
    return buckets
  }, [tasksState])

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-[400px] w-full" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Eisenhower Matrix</h2>
          <p className="text-sm text-gray-400 mt-1">
            Organize tasks by urgency and importance
          </p>
        </div>
        {refresh && (
          <Button variant="outline" size="sm" onClick={refresh}>
            Refresh
          </Button>
        )}
      </div>

      {/* Matrix Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Q1: Urgent & Important (Top Left) */}
        <QuadrantCard
          title="Q1: Do First"
          description="Urgent & Important - Handle immediately"
          tasks={quadrantBuckets.Q1}
          bgColor="bg-red-100 dark:bg-red-900/20"
          borderColor="border-red-200 dark:border-red-700"
          icon="🔴"
          onDrop={handleDrop("Q1")}
          onResetTask={handleReset}
          onDragStartTask={onDragStart}
          onDropTask={(taskId) => handleDropOnTask("Q1", taskId)}
        />

        {/* Q2: Not Urgent, Important (Top Right) */}
        <QuadrantCard
          title="Q2: Schedule"
          description="Not Urgent, Important - Plan for later"
          tasks={quadrantBuckets.Q2}
          bgColor="bg-green-100 dark:bg-green-900/20"
          borderColor="border-green-200 dark:border-green-700"
          icon="🟢"
          onDrop={handleDrop("Q2")}
          onResetTask={handleReset}
          onDragStartTask={onDragStart}
          onDropTask={(taskId) => handleDropOnTask("Q2", taskId)}
        />

        {/* Q3: Urgent, Not Important (Bottom Left) */}
        <QuadrantCard
          title="Q3: Delegate"
          description="Urgent, Not Important - Consider delegating"
          tasks={quadrantBuckets.Q3}
          bgColor="bg-yellow-100 dark:bg-yellow-900/20"
          borderColor="border-yellow-200 dark:border-yellow-700"
          icon="🟡"
          onDrop={handleDrop("Q3")}
          onResetTask={handleReset}
          onDragStartTask={onDragStart}
          onDropTask={(taskId) => handleDropOnTask("Q3", taskId)}
        />

        {/* Q4: Neither (Bottom Right) */}
        <QuadrantCard
          title="Q4: Eliminate"
          description="Neither Urgent nor Important - Minimize time"
          tasks={quadrantBuckets.Q4}
          bgColor="bg-blue-100 dark:bg-blue-900/20"
          borderColor="border-blue-200 dark:border-blue-700"
          icon="🔵"
          onDrop={handleDrop("Q4")}
          onResetTask={handleReset}
          onDragStartTask={onDragStart}
          onDropTask={(taskId) => handleDropOnTask("Q4", taskId)}
        />
      </div>

      {savingTaskId && (
        <div className="text-xs text-gray-400">
          Updating task #{savingTaskId}...
        </div>
      )}
    </div>
  )
}
