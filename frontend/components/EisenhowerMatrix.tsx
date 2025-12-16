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
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Progress } from "@/components/ui/progress"
import { api } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, ChevronDown, ChevronUp, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { SortableCard } from "@/components/dnd/SortableCard"
import { getQuadrant } from "@/lib/taskUtils"

import { Task, TasksResponse } from "@/types/task"

interface EisenhowerMatrixProps {
  tasks?: Task[]
  onTasksUpdate?: (tasks: Task[]) => void
  refresh?: () => Promise<void>
}

// --- Components ---

function SortableTask({ task, isActiveOverlay, onReset }: { task: Task, isActiveOverlay?: boolean, onReset?: () => void }) {
  // If this is the overlay, render without sortable wrappers
  if (isActiveOverlay) {
    return <TaskCardInner task={task} isOverlay onReset={onReset} />
  }

  return (
    <SortableCard
      id={task.id}
      data={{ type: "Task", task }}
      className="mb-2 touch-none"
      draggingClassName="opacity-30"
    >
      {() => <TaskCardInner task={task} onReset={onReset} />}
    </SortableCard>
  )
}

function TaskCardInner({ task, isOverlay, onReset }: { task: Task, isOverlay?: boolean, onReset?: () => void }) {
  const [expanded, setExpanded] = useState(false)

  const truncatedReasoning = task.analysis_reasoning
    ? task.analysis_reasoning.length > 120
      ? task.analysis_reasoning.substring(0, 120) + "..."
      : task.analysis_reasoning
    : "No AI analysis available"

  return (
    <Popover>
      <PopoverTrigger asChild>
        <div
          className={`
                        w-full text-left p-3 rounded-lg bg-background border border-border 
                        transition-all cursor-grab active:cursor-grabbing
                        ${isOverlay ? 'shadow-xl scale-105 border-primary ring-1 ring-primary' : 'hover:bg-accent/50 shadow-sm'}
                    `}
        >
          <div className="flex justify-between items-start pointer-events-none">
            <p className="text-sm font-medium text-foreground truncate pr-2">
              {task.title}
            </p>
          </div>

          <div className="flex items-center gap-2 mt-1 pointer-events-none">
            <span className="text-xs text-muted-foreground bg-secondary/50 px-1 rounded">U: {task.urgency_score ?? 0}</span>
            <span className="text-xs text-muted-foreground bg-secondary/50 px-1 rounded">I: {task.importance_score ?? 0}</span>
          </div>
        </div>
      </PopoverTrigger>

      {/* 
               We disable the popover content while purely acting as an overlay OR while dragging 
               But SortableTask logic handles dragging. `isOverlay` is true when it's the "ghost" following mouse.
               We usually don't want the popover to open on the overlay.
            */}
      {!isOverlay && (
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

            <div className="flex gap-4">
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-gray-400">Urgency</span>
                  <span className="text-xs font-semibold text-gray-300">
                    {task.urgency_score ?? 0}/10
                  </span>
                </div>
                <Progress value={(task.urgency_score ?? 0) * 10} className="h-1.5" />
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-gray-400">Importance</span>
                  <span className="text-xs font-semibold text-gray-300">
                    {task.importance_score ?? 0}/10
                  </span>
                </div>
                <Progress value={(task.importance_score ?? 0) * 10} className="h-1.5" />
              </div>
            </div>

            <div className="border-t border-border pt-3 mt-2">
              <div className="flex items-start gap-2">
                <span className="text-base">💡</span>
                <div className="flex-1">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {expanded ? task.analysis_reasoning : truncatedReasoning}
                  </p>
                </div>
              </div>

              {task.analysis_reasoning && task.analysis_reasoning.length > 120 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setExpanded(!expanded)}
                  className="w-full mt-2 text-xs text-muted-foreground hover:text-foreground h-6"
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

            <div className="flex items-center justify-between pt-2 border-t border-border">
              <span className="text-[10px] text-muted-foreground">
                {task.created_at ? new Date(task.created_at).toLocaleDateString() : ""}
              </span>
              {task.manual_quadrant_override && (
                <Badge variant="outline" className="text-[10px]">
                  Manual override
                </Badge>
              )}
            </div>

            {task.manual_quadrant_override && (
              <div className="mt-3 flex items-center justify-between border-t border-gray-700 pt-3">
                <div className="text-xs text-gray-400">
                  Override: {task.manual_quadrant_override}
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
      )}
    </Popover>
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
}: {
  title: string
  description: string
  tasks: Task[]
  bgColor: string
  borderColor: string
  icon: string
  quadrantId: string
  onResetTask?: (taskId: number) => void
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
                onReset={onResetTask ? () => onResetTask(task.id) : undefined}
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
    const { active, over } = event
    const id = active.id as number

    // Cleanup active state
    setActiveId(null)
    setActiveTask(null)

    if (!over) return;

    const currentQuadrants = quadrantIdsRef.current
    const activeContainer = findContainer(active.id as number)
    const overContainer = (Object.keys(currentQuadrants).includes(over.id as string))
      ? over.id as string
      : findContainer(over.id as number)

    if (activeContainer && overContainer) {
      // Calculate final index in the destination using the latest state
      const overIndex = currentQuadrants[overContainer].indexOf(over.id as number)
      const activeIndex = currentQuadrants[activeContainer].indexOf(active.id as number)

      if (activeContainer === overContainer) {
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
        // Moved between containers 
        // 1. Update task metadata (quadrant)
        await persistQuadrantChange(id, overContainer)

        // 2. Persist order of destination container
        // The state `quadrantIds` is already updated by `handleDragOver`.
        const newOrder = quadrantIds[overContainer]
        await persistReorder(overContainer, newOrder)
      }
    }
  }

  const findContainer = (id: number) => {
    return Object.keys(quadrantIds).find(key => quadrantIds[key].includes(id));
  }

  const persistQuadrantChange = async (taskId: number, newQuadrant: string) => {
    try {
      // Optimistic task update
      setTasksState(prev => prev.map(t => {
        if (t.id === taskId) {
          return { ...t, manual_quadrant_override: newQuadrant, manual_override_reason: "Moved in matrix" }
        }
        return t
      }))

      await api.patch(`/api/tasks/${taskId}/quadrant`, {
        manual_quadrant: newQuadrant,
        reason: "Moved in matrix view",
        source: "matrix"
      })
    } catch (err) {
      console.error("Failed to update quadrant", err)
    }
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
    } catch (err) {
      console.error("Reorder failed", err)
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
      if (onTasksUpdate) onTasksUpdate(tasksState.map(t => t.id === taskId ? updated : t))
    } catch (err: any) {
      setError(err.message || "Failed to reset override")
    } finally {
      setSavingTaskId(null)
    }
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
          />
        </div>

        <DragOverlay dropAnimation={dropAnimation}>
          {activeTask ? <SortableTask task={activeTask} isActiveOverlay /> : null}
        </DragOverlay>
      </DndContext>

      {savingTaskId && (
        <div className="text-xs text-gray-400 fixed bottom-4 right-4 bg-background border border-border p-2 rounded shadow">
          Updating task...
        </div>
      )}
    </div>
  )
}
