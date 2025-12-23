"use client"

import { useEffect, useState, useRef } from "react"
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragOverEvent,
  DragEndEvent,
  defaultDropAnimationSideEffects,
  DropAnimation
} from "@dnd-kit/core"
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle } from "lucide-react"
import { SortableCard } from "@/components/dnd/SortableCard"
import { getQuadrant } from "@/lib/taskUtils"
import { toast } from "sonner"
import { UnsortedItemsSection } from "@/components/UnsortedItemsSection"
import { TaskDetailPopover } from "@/components/TaskDetailPopover"

import { Task, TasksResponse } from "@/types/task"

interface EisenhowerMatrixProps {
  tasks?: Task[]
  onTasksUpdate?: () => void | Promise<void>
  refresh?: () => Promise<void>
}

// --- Components ---

function SortableTask({
  task,
  isActiveOverlay,
  onUpdate,
  onDelete
}: {
  task: Task
  isActiveOverlay?: boolean
  onUpdate?: (task: Task) => void
  onDelete?: (taskId: number) => void
}) {
  // If this is the overlay, render without sortable wrappers
  if (isActiveOverlay) {
    return <TaskCardInner task={task} isOverlay />
  }

  return (
    <SortableCard
      id={task.id}
      data={{ type: "Task", task }}
      className="mb-2 touch-none"
      draggingClassName="opacity-30"
    >
      {() => <TaskCardInner task={task} onUpdate={onUpdate} onDelete={onDelete} />}
    </SortableCard>
  )
}

function TaskCardInner({
  task,
  isOverlay,
  onUpdate,
  onDelete
}: {
  task: Task
  isOverlay?: boolean
  onUpdate?: (task: Task) => void
  onDelete?: (taskId: number) => void
}) {
  // If this is the drag overlay, render simple display only
  if (isOverlay) {
    return (
      <div className="w-full text-left p-3 rounded-lg bg-card border shadow-lg">
        <div className="text-sm font-medium mb-1">{task.title}</div>
      </div>
    )
  }

  // Normal task card with TaskDetailPopover
  return (
    <TaskDetailPopover
      task={task}
      onUpdate={(updatedTask) => {
        onUpdate?.(updatedTask)
      }}
      onDelete={(taskId) => {
        onDelete?.(taskId)
      }}
      trigger={
        <div className="w-full text-left p-3 rounded-lg bg-card border hover:bg-accent/50 transition-colors cursor-pointer">
          <div className="text-sm font-medium mb-1">{task.title}</div>
          {task.description && (
            <p className="text-xs text-muted-foreground line-clamp-2">
              {task.description}
            </p>
          )}
          {/* Quadrant badge */}
          <div className="mt-2 flex gap-1">
            {getQuadrant(task) && (
              <Badge variant="outline" className="text-xs">
                {getQuadrant(task)}
              </Badge>
            )}
            {task.manual_quadrant_override && (
              <Badge variant="secondary" className="text-xs">
                Manual
              </Badge>
            )}
          </div>
        </div>
      }
    />
  )
}

const QuadrantCard = ({
  title,
  description,
  tasks,
  bgColor,
  borderColor,
  icon,
  quadrantId,
  onResetTask,
  onUpdateTask,
  onDeleteTask,
}: {
  title: string
  description: string
  tasks: Task[]
  bgColor: string
  borderColor: string
  icon: string
  quadrantId: string
  onResetTask?: (taskId: number) => void
  onUpdateTask?: (task: Task) => void
  onDeleteTask?: (taskId: number) => void
}) => {
  return (
    <Card
      className={`p-6 ${bgColor} ${borderColor} border-2 h-full min-h-[300px] flex flex-col transition-colors duration-200`}
    >
      <div className="mb-4 pointer-events-none select-none">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">{icon}</span>
          <h3 className="text-lg font-bold text-foreground">{title}</h3>
        </div>
        <p className="text-xs text-muted-foreground">{description}</p>
        <Badge variant="secondary" className="mt-2">
          {tasks.length} {tasks.length === 1 ? "task" : "tasks"}
        </Badge>
      </div>

      <div className="flex-1 overflow-y-auto max-h-[400px] overflow-x-visible p-1 min-h-[100px]">
        <SortableContext
          id={quadrantId}
          items={tasks.map(t => t.id)}
          strategy={verticalListSortingStrategy}
        >
          {tasks.length === 0 ? (
            <div className="h-32 w-full flex items-center justify-center text-sm text-gray-500/50 italic border-2 border-dashed border-gray-500/10 rounded-lg">
              Drop here
            </div>
          ) : (
            tasks.map((task) => (
              <SortableTask
                key={task.id}
                task={task}
                onUpdate={onUpdateTask}
                onDelete={onDeleteTask}
              />
            ))
          )}
        </SortableContext>
      </div>
    </Card>
  )
}

export function EisenhowerMatrix({ tasks, onTasksUpdate, refresh }: EisenhowerMatrixProps) {
  const controlled = Boolean(tasks && onTasksUpdate)
  const [tasksState, setTasksState] = useState<Task[]>(tasks ?? [])
  const [loading, setLoading] = useState(!controlled)
  const [error, setError] = useState<string | null>(null)
  const [activeId, setActiveId] = useState<number | null>(null)
  const [activeTask, setActiveTask] = useState<Task | null>(null)
  const [savingTaskId, setSavingTaskId] = useState<number | null>(null)
  const [savingDrag, setSavingDrag] = useState(false)

  // Ref to prevent race conditions from rapid successive drags
  const dragLockRef = useRef(false)

  // Track the original container when drag starts (before handleDragOver modifies state)
  const originalContainerRef = useRef<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      // Require a slight move before activating drag so clicks still open the popover
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Helper to split tasks into buckets
  const getBuckets = (taskList: Task[]) => {
    const buckets: Record<string, Task[]> = { Q1: [], Q2: [], Q3: [], Q4: [] }
    taskList.forEach(task => {
      const q = getQuadrant(task)
      if (q && buckets[q]) buckets[q].push(task)
    })

    // Sort each bucket by manual_order or createdAt
    Object.keys(buckets).forEach(key => {
      buckets[key].sort((a, b) => {
        const aOrder = a.manual_order ?? 999999
        const bOrder = b.manual_order ?? 999999
        if (aOrder !== bOrder) return aOrder - bOrder
        const bTime = b.created_at ? new Date(b.created_at).getTime() : 0
        const aTime = a.created_at ? new Date(a.created_at).getTime() : 0
        return bTime - aTime
      })
    })
    return buckets
  }

  // State to track order in each quadrant
  const [quadrantIds, setQuadrantIds] = useState<Record<string, number[]>>({ Q1: [], Q2: [], Q3: [], Q4: [] })
  const quadrantIdsRef = useRef(quadrantIds)

  const arraysEqual = (a: number[], b: number[]) =>
    a.length === b.length && a.every((val, idx) => val === b[idx])

  const quadrantsEqual = (next: Record<string, number[]>, prev: Record<string, number[]>) =>
    ["Q1", "Q2", "Q3", "Q4"].every(key => arraysEqual(next[key], prev[key]))

  // Keep a ref in sync for async handlers that need the latest order
  useEffect(() => {
    quadrantIdsRef.current = quadrantIds
  }, [quadrantIds])

  // Initialize Quadrant State from Tasks
  useEffect(() => {
    // If we are actively dragging, DO NOT SYNC from props/API, or we lose position.
    if (activeId) return;

    if (tasksState.length > 0) {
      const buckets = getBuckets(tasksState);
      const next = {
        Q1: buckets.Q1.map(t => t.id),
        Q2: buckets.Q2.map(t => t.id),
        Q3: buckets.Q3.map(t => t.id),
        Q4: buckets.Q4.map(t => t.id),
      }

      setQuadrantIds(prev => quadrantsEqual(next, prev) ? prev : next)
    }
  }, [tasksState, activeId]);


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
      setTasksState(response.tasks || [])
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


  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    setActiveId(active.id as number)
    setActiveTask(tasksState.find(t => t.id === active.id) || null)

    // Store the original container before handleDragOver modifies state
    originalContainerRef.current = findContainer(active.id as number) || null
  }

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event
    if (!over) return

    // Find the containers
    const activeContainer = findContainer(active.id as number)
    const overContainer = (Object.keys(quadrantIds).includes(over.id as string))
      ? over.id as string
      : findContainer(over.id as number)

    if (!activeContainer || !overContainer || activeContainer === overContainer) {
      return
    }

    // Moving between quadrants
    setQuadrantIds(prev => {
      const activeItems = prev[activeContainer] || []
      const overItems = prev[overContainer] || []

      const activeIndex = activeItems.indexOf(active.id as number)
      if (activeIndex === -1) return prev

      const overIndex = (Object.keys(prev).includes(over.id as string))
        ? overItems.length // place at end of container
        : overItems.indexOf(over.id as number)

      const isBelowOverItem = over &&
        active.rect.current.translated &&
        active.rect.current.translated.top > over.rect.top + over.rect.height

      const modifier = isBelowOverItem ? 1 : 0
      const newIndex = overIndex >= 0 ? overIndex + modifier : overItems.length
      const clampedIndex = Math.max(0, Math.min(newIndex, overItems.length))

      const nextActive = activeItems.filter(item => item !== active.id)
      const nextOver = [...overItems]
      nextOver.splice(clampedIndex, 0, active.id as number)

      const nextState = {
        ...prev,
        [activeContainer]: nextActive,
        [overContainer]: nextOver
      }

      return quadrantsEqual(nextState, prev) ? prev : nextState
    })
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    // Prevent race conditions from rapid successive drags
    if (dragLockRef.current) return

    dragLockRef.current = true

    try {
      const { active, over } = event
      const id = active.id as number

      // Cleanup active state
      setActiveId(null)
      setActiveTask(null)

      if (!over) {
        originalContainerRef.current = null
        return
      }

      const currentQuadrants = quadrantIdsRef.current

      // Use the original container from when drag started (before handleDragOver modified state)
      const activeContainer = originalContainerRef.current

      // Determine the target container
      const overContainer = (Object.keys(currentQuadrants).includes(over.id as string))
        ? over.id as string
        : findContainer(over.id as number)

      console.log("Drag end:", { activeContainer, overContainer, taskId: id })

      if (activeContainer && overContainer) {
        // Calculate final index in the destination using the latest state
        const overIndex = currentQuadrants[overContainer].indexOf(over.id as number)
        const activeIndex = currentQuadrants[activeContainer].indexOf(active.id as number)

        if (activeContainer === overContainer) {
          // Same quadrant: only reorder
          if (activeIndex !== overIndex) {
            const newOrder = arrayMove(currentQuadrants[activeContainer], activeIndex, overIndex)
            setQuadrantIds(prev => ({
              ...prev,
              [activeContainer]: newOrder
            }))
            // Persist Order
            await persistReorder(activeContainer, newOrder)
          }
        } else {
          // Cross-quadrant move
          setSavingDrag(true)

          try {
            console.log(`Moving task ${id} from ${activeContainer} to ${overContainer}`)

            // 1. Update quadrant (backend auto-assigns manual_order to end)
            const response = await api.patch(`/api/tasks/${id}/quadrant`, {
              manual_quadrant: overContainer,
              reason: "Moved in matrix view",
              source: "matrix"
            })

            console.log("Quadrant update response:", response)

            // 2. Refresh from server to get updated task state
            if (controlled && onTasksUpdate) {
              await onTasksUpdate() // Trigger parent refresh in controlled mode
            } else {
              await fetchTasks() // Fetch tasks in uncontrolled mode
            }

            toast.success(`Task moved to ${overContainer}`)
          } catch (err: any) {
            console.error("Failed to move task:", {
              error: err,
              message: err?.message,
              data: err?.data,
              taskId: id,
              from: activeContainer,
              to: overContainer
            })

            // Rollback: restore quadrantIds from current tasksState
            const buckets = getBuckets(tasksState)
            setQuadrantIds({
              Q1: buckets.Q1.map(t => t.id),
              Q2: buckets.Q2.map(t => t.id),
              Q3: buckets.Q3.map(t => t.id),
              Q4: buckets.Q4.map(t => t.id),
            })

            toast.error(err?.message || "Failed to move task. Changes reverted.")
          } finally {
            setSavingDrag(false)
          }
        }
      }
    } finally {
      dragLockRef.current = false
      originalContainerRef.current = null
    }
  }

  const findContainer = (id: number) => {
    return Object.keys(quadrantIds).find(key => quadrantIds[key].includes(id));
  }

  const persistReorder = async (quadrant: string, orderedIds: number[]) => {
    try {
      // Update local task state manual_order for consistency
      setTasksState(prev => {
        return prev.map(t => {
          const idx = orderedIds.indexOf(t.id)
          if (idx !== -1 && (t.manual_quadrant_override === quadrant || t.eisenhower_quadrant === quadrant || t.effective_quadrant === quadrant)) {
            return { ...t, manual_order: idx }
          }
          return t
        })
      })

      await api.post("/api/tasks/reorder", {
        user_id: 1,
        quadrant,
        task_ids: orderedIds,
      })
    } catch (err: any) {
      console.error("Reorder failed:", {
        error: err,
        message: err?.message || 'Unknown error',
        quadrant,
        taskCount: orderedIds.length
      })
      // Don't show error toast for reorder within same quadrant - it's not critical
      // The optimistic update already happened, and next fetch will correct any inconsistencies
    }
  }

  const handleReset = async (taskId: number) => {
    setSavingTaskId(taskId)
    setError(null)
    try {
      const updated = await api.patch<Task>(`/api/tasks/${taskId}/quadrant`, {
        reset_to_ai: true,
      })
      // Updates state
      setTasksState(prev => prev.map(t => t.id === taskId ? updated : t))
      if (onTasksUpdate) onTasksUpdate()
    } catch (err: any) {
      setError(err.message || "Failed to reset override")
    } finally {
      setSavingTaskId(null)
    }
  }

  const handleUpdateTask = (updatedTask: Task) => {
    setTasksState(prev => prev.map(t => t.id === updatedTask.id ? updatedTask : t))
    if (onTasksUpdate) onTasksUpdate()
  }

  const handleDeleteTask = (taskId: number) => {
    setTasksState(prev => prev.filter(t => t.id !== taskId))
    // Also remove from quadrantIds
    setQuadrantIds(prev => {
      const findContainer = (id: number) => {
        return Object.keys(prev).find(key => prev[key].includes(id))
      }
      const quadrant = findContainer(taskId)
      if (quadrant) {
        return {
          ...prev,
          [quadrant]: prev[quadrant].filter(id => id !== taskId)
        }
      }
      return prev
    })
    if (onTasksUpdate) onTasksUpdate()
  }

  const dropAnimation: DropAnimation = {
    sideEffects: defaultDropAnimationSideEffects({
      styles: {
        active: {
          opacity: '0.5',
        },
      },
    }),
  }

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

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <QuadrantCard
            title="Q1: Do First"
            description="Urgent & Important"
            tasks={quadrantIds.Q1.map(id => tasksState.find(t => t.id === id)).filter(Boolean) as Task[]}
            bgColor="bg-red-500/10"
            borderColor="border-red-500/20"
            icon="🔴"
            quadrantId="Q1"
            onResetTask={handleReset}
            onUpdateTask={handleUpdateTask}
            onDeleteTask={handleDeleteTask}
          />

          <QuadrantCard
            title="Q2: Schedule"
            description="Not Urgent, Important"
            tasks={quadrantIds.Q2.map(id => tasksState.find(t => t.id === id)).filter(Boolean) as Task[]}
            bgColor="bg-green-500/10"
            borderColor="border-green-500/20"
            icon="🟢"
            quadrantId="Q2"
            onResetTask={handleReset}
            onUpdateTask={handleUpdateTask}
            onDeleteTask={handleDeleteTask}
          />

          <QuadrantCard
            title="Q3: Delegate"
            description="Urgent, Not Important"
            tasks={quadrantIds.Q3.map(id => tasksState.find(t => t.id === id)).filter(Boolean) as Task[]}
            bgColor="bg-yellow-500/10"
            borderColor="border-yellow-500/20"
            icon="🟡"
            quadrantId="Q3"
            onResetTask={handleReset}
            onUpdateTask={handleUpdateTask}
            onDeleteTask={handleDeleteTask}
          />

          <QuadrantCard
            title="Q4: Eliminate"
            description="Neither Urgent nor Important"
            tasks={quadrantIds.Q4.map(id => tasksState.find(t => t.id === id)).filter(Boolean) as Task[]}
            bgColor="bg-blue-500/10"
            borderColor="border-blue-500/20"
            icon="🔵"
            quadrantId="Q4"
            onResetTask={handleReset}
            onUpdateTask={handleUpdateTask}
            onDeleteTask={handleDeleteTask}
          />
        </div>

        <DragOverlay dropAnimation={dropAnimation}>
          {activeTask ? <SortableTask task={activeTask} isActiveOverlay /> : null}
        </DragOverlay>
      </DndContext>

      {/* Unsorted Items Section */}
      <UnsortedItemsSection
        activeId={activeId}
        onTaskSorted={(taskId, quadrant) => {
          // Refresh matrix tasks to show newly assigned item
          if (controlled && onTasksUpdate) {
            onTasksUpdate() // Trigger parent refresh in controlled mode
          } else {
            fetchTasks() // Fetch tasks in uncontrolled mode
          }
        }}
        onRefresh={async () => { controlled && onTasksUpdate ? await onTasksUpdate() : fetchTasks(); }}
      />

      {savingTaskId && (
        <div className="text-xs text-gray-400 fixed bottom-4 right-4 bg-background border border-border p-2 rounded shadow">
          Updating task...
        </div>
      )}
    </div>
  )
}
