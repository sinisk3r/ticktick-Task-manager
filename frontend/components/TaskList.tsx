"use client"

import { useEffect, useMemo, useState } from "react"
import useSWR from "swr"
import { toast } from "sonner"
import { formatISO, startOfDay, endOfDay, endOfWeek } from "date-fns"
import { useRouter, useSearchParams } from "next/navigation"
import { TaskCard } from "./TaskCard"
import { QuadrantFilter } from "./QuadrantFilter"
import { EisenhowerMatrix } from "./EisenhowerMatrix"
import { ListTaskCard } from "./ListTaskCard"
import { api, API_BASE } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AlertCircle,
  LayoutGrid,
  List,
  Trash2,
  Layers,
  CheckCircle2,
  Rows,
  Columns3,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { getQuadrant } from "@/lib/taskUtils"
import { Badge } from "@/components/ui/badge"
import { Task, TasksResponse, TaskSummary } from "@/types/task"
import { ProjectSelector } from "./metadata/ProjectSelector"
import { TaskDetailPopover } from "./TaskDetailPopover"

type TaskStatus = "active" | "completed" | "deleted"
type ListLayout = "vertical" | "horizontal"
type DueFilter = "all" | "today" | "week" | "overdue"
type SortBy = "created" | "due_date" | "priority" | "title"

const fetcher = (url: string) => fetch(url).then((r) => r.json())

export function TaskList() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const statusParam = (searchParams.get("status") as TaskStatus) || "active"

  const [statusFilter, setStatusFilter] = useState<TaskStatus>(statusParam)
  const [quadrantFilter, setQuadrantFilter] = useState<string | null>(null)
  const [projectFilter, setProjectFilter] = useState<number | null>(null)
  const [tagFilter, setTagFilter] = useState<string>("")
  const [dueFilter, setDueFilter] = useState<DueFilter>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [sortBy, setSortBy] = useState<SortBy>("created")
  const [viewMode, setViewMode] = useState<"matrix" | "list">("matrix")
  const [listLayout, setListLayout] = useState<ListLayout>("vertical")

  // Sync state with URL param if it changes
  useEffect(() => {
    setStatusFilter(statusParam)
  }, [statusParam])

  // Update URL when status filter changes manually
  const handleStatusChange = (newStatus: TaskStatus) => {
    setStatusFilter(newStatus)
    const params = new URLSearchParams(searchParams.toString())
    if (newStatus === "active") params.delete("status")
    else params.set("status", newStatus)
    router.push(`?${params.toString()}`)
  }

  // Force matrix off for non-active statuses
  useEffect(() => {
    if (statusFilter !== "active" && viewMode === "matrix") {
      setViewMode("list")
    }
  }, [statusFilter, viewMode])

  const buildQuery = () => {
    const params = new URLSearchParams({
      user_id: "1",
      limit: "300",
      status: statusFilter,
    })

    if (quadrantFilter && statusFilter === "active") params.append("quadrant", quadrantFilter)
    if (projectFilter) params.append("project_id", String(projectFilter))
    if (tagFilter.trim()) params.append("tag", tagFilter.trim())
    if (searchQuery.trim()) params.append("search", searchQuery.trim())

    const now = new Date()
    if (dueFilter === "today") {
      params.append("due_after", formatISO(startOfDay(now)))
      params.append("due_before", formatISO(endOfDay(now)))
    } else if (dueFilter === "week") {
      params.append("due_after", formatISO(startOfDay(now)))
      params.append("due_before", formatISO(endOfWeek(now)))
    } else if (dueFilter === "overdue") {
      params.append("due_before", formatISO(now))
    }

    return params.toString()
  }

  const tasksUrl = `${API_BASE}/api/tasks?${buildQuery()}`

  const { data, error, isLoading, mutate } = useSWR<TasksResponse>(
    tasksUrl,
    fetcher,
    { refreshInterval: 15000 }
  )

  const { data: summary } = useSWR<TaskSummary>(
    `${API_BASE}/api/tasks/summary?user_id=1`,
    fetcher,
    { refreshInterval: 20000 }
  )

  const tasks = data?.tasks || []

  const handleTaskUpdate = (updatedTask: Task) => {
    mutate((current) => {
      if (!current) return current
      // Remove task if status no longer matches filter
      if (statusFilter === "active" && updatedTask.status !== "active") {
        return { ...current, tasks: current.tasks.filter((t) => t.id !== updatedTask.id) }
      }
      if (statusFilter === "completed" && updatedTask.status !== "completed") {
        return { ...current, tasks: current.tasks.filter((t) => t.id !== updatedTask.id) }
      }
      if (statusFilter === "deleted" && updatedTask.status !== "deleted") {
        return { ...current, tasks: current.tasks.filter((t) => t.id !== updatedTask.id) }
      }
      return {
        ...current,
        tasks: current.tasks.map((t) => (t.id === updatedTask.id ? updatedTask : t)),
      }
    }, false)
  }

  const handleTaskDelete = (taskId: number) => {
    mutate(
      (current) => {
        if (!current) return current
        return { ...current, tasks: current.tasks.filter((t) => t.id !== taskId) }
      },
      false
    )
  }

  const handleToggleStatus = async (task: Task) => {
    const newStatus = task.status === "completed" ? "active" : "completed"
    const optimistic = { ...task, status: newStatus }
    handleTaskUpdate(optimistic)

    try {
      await api.patch(`/api/tasks/${task.id}`, { status: newStatus, user_id: 1 })
      mutate()
      toast.success(newStatus === "completed" ? "Task completed" : "Task reopened")
    } catch (err) {
      console.error("Failed to toggle task status", err)
      toast.error("Could not update task")
      handleTaskUpdate(task) // revert
    }
  }

  const handleRefresh = async () => {
    await mutate()
    await mutate(`${API_BASE}/api/tasks/summary?user_id=1`)
  }

  const taskCounts = useMemo(() => {
    if (summary) {
      return {
        all: summary.total_active,
        Q1: summary.quadrants.Q1 || 0,
        Q2: summary.quadrants.Q2 || 0,
        Q3: summary.quadrants.Q3 || 0,
        Q4: summary.quadrants.Q4 || 0,
      }
    }
    return {
      all: tasks.length,
      Q1: tasks.filter((t) => getQuadrant(t) === "Q1").length,
      Q2: tasks.filter((t) => getQuadrant(t) === "Q2").length,
      Q3: tasks.filter((t) => getQuadrant(t) === "Q3").length,
      Q4: tasks.filter((t) => getQuadrant(t) === "Q4").length,
    }
  }, [summary, tasks])

  const sortedTasks = useMemo(() => {
    const next = [...tasks]
    return next.sort((a, b) => {
      switch (sortBy) {
        case "due_date": {
          const aTime = a.due_date ? new Date(a.due_date).getTime() : Infinity
          const bTime = b.due_date ? new Date(b.due_date).getTime() : Infinity
          return aTime - bTime
        }
        case "priority":
          return (b.ticktick_priority || 0) - (a.ticktick_priority || 0)
        case "title":
          return a.title.localeCompare(b.title)
        case "created":
        default: {
          const bTime = b.created_at ? new Date(b.created_at).getTime() : 0
          const aTime = a.created_at ? new Date(a.created_at).getTime() : 0
          return bTime - aTime
        }
      }
    })
  }, [tasks, sortBy])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="mb-6">
          <Skeleton className="h-10 w-48" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between gap-3">
          <span>{error?.message || "Failed to load tasks"}</span>
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as "matrix" | "list")} className="w-full">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <TabsList>
            <TabsTrigger value="matrix" disabled={statusFilter !== "active"}>
              <LayoutGrid className="h-4 w-4 mr-2" />
              Matrix
            </TabsTrigger>
            <TabsTrigger value="list">
              <List className="h-4 w-4 mr-2" />
              List
            </TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-2">
            {viewMode === "list" && (
              <div className="flex rounded-md border overflow-hidden">
                <Button
                  variant={listLayout === "vertical" ? "default" : "ghost"}
                  size="sm"
                  className="rounded-none h-9 px-3"
                  onClick={() => setListLayout("vertical")}
                >
                  <Rows className="h-4 w-4 mr-2" />
                  Vertical
                </Button>
                <Button
                  variant={listLayout === "horizontal" ? "default" : "ghost"}
                  size="sm"
                  className="rounded-none h-9 px-3"
                  onClick={() => setListLayout("horizontal")}
                >
                  <Columns3 className="h-4 w-4 mr-2" />
                  Horizontal
                </Button>
              </div>
            )}
          </div>
        </div>

        <div className="bg-card p-4 rounded-lg border space-y-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-3 items-center">
            {/* Search - Spans larger */}
            <div className="lg:col-span-4">
              <Input
                placeholder="Search title, description, project..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Status Filter */}
            <div className="lg:col-span-2">
              <Select value={statusFilter} onValueChange={(v) => handleStatusChange(v as TaskStatus)}>
                <SelectTrigger>
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">
                    <div className="flex items-center gap-2">
                      <Layers className="h-4 w-4" />
                      <span>Active</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="completed">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Done</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="deleted">
                    <div className="flex items-center gap-2">
                      <Trash2 className="h-4 w-4" />
                      <span>Bin</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Other Filters */}
            <div className="lg:col-span-2">
              <Select value={dueFilter} onValueChange={(v) => setDueFilter(v as DueFilter)}>
                <SelectTrigger>
                  <SelectValue placeholder="Due date" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any date</SelectItem>
                  <SelectItem value="today">Due today</SelectItem>
                  <SelectItem value="week">Due this week</SelectItem>
                  <SelectItem value="overdue">Overdue</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="lg:col-span-2">
              <ProjectSelector
                value={projectFilter}
                onChange={(id) => setProjectFilter(id)}
                placeholder="Project"
              />
            </div>

            <div className="lg:col-span-2">
              <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortBy)}>
                <SelectTrigger>
                  <SelectValue placeholder="Sort" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created">Created</SelectItem>
                  <SelectItem value="due_date">Due Date</SelectItem>
                  <SelectItem value="priority">Priority</SelectItem>
                  <SelectItem value="title">Title</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {statusFilter === "active" && (
            <QuadrantFilter
              selectedQuadrant={quadrantFilter}
              onQuadrantChange={setQuadrantFilter}
              taskCounts={taskCounts}
            />
          )}
        </div>

        <TabsContent value="matrix" className="mt-0">
          {statusFilter === "active" ? (
            <EisenhowerMatrix tasks={sortedTasks} onTasksUpdate={() => mutate()} />
          ) : (
            <div className="text-center py-12 border-2 border-dashed rounded-lg">
              <p className="text-muted-foreground">Matrix view is only available for active tasks.</p>
              <Button variant="link" onClick={() => setViewMode("list")}>Switch to List View</Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="list" className="mt-0">
          {sortedTasks.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No tasks found. Try adjusting filters.</p>
            </div>
          ) : listLayout === "vertical" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedTasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onUpdate={handleTaskUpdate}
                  onDelete={handleTaskDelete}
                  onToggleStatus={handleToggleStatus}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {sortedTasks.map((task) => (
                <TaskDetailPopover
                  key={task.id}
                  task={task}
                  onUpdate={handleTaskUpdate}
                  onDelete={handleTaskDelete}
                  trigger={
                    <ListTaskCard task={task} onToggleStatus={handleToggleStatus} />
                  }
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
