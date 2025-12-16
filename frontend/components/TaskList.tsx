"use client"

import { useState, useEffect } from "react"
import { toast } from "sonner"
import { TaskCard } from "./TaskCard"
import { QuadrantFilter } from "./QuadrantFilter"
import { EisenhowerMatrix } from "./EisenhowerMatrix"
import { api } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw, LayoutGrid, List, CheckCircle2, Trash2, Layers } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { getQuadrant } from "@/lib/taskUtils"

import { Task, TasksResponse } from "@/types/task"

type TaskStatus = "active" | "completed" | "deleted"

export function TaskList() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedQuadrant, setSelectedQuadrant] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [currentStatus, setCurrentStatus] = useState<TaskStatus>("active")
  const [viewMode, setViewMode] = useState<"matrix" | "list">("matrix")

  // Calculate task counts by quadrant
  const taskCounts = {
    all: tasks.length,
    Q1: tasks.filter((t) => getQuadrant(t) === "Q1").length,
    Q2: tasks.filter((t) => getQuadrant(t) === "Q2").length,
    Q3: tasks.filter((t) => getQuadrant(t) === "Q3").length,
    Q4: tasks.filter((t) => getQuadrant(t) === "Q4").length,
  }

  const fetchTasks = async () => {
    try {
      setLoading(true)
      setError(null)

      // Build query parameters
      const params = new URLSearchParams({
        user_id: "1", // Hardcoded for single-user mode
        status: currentStatus,
        limit: "100",
      })

      if (selectedQuadrant && currentStatus === "active") {
        params.append("quadrant", selectedQuadrant)
      }

      const response = await api.get<TasksResponse>(
        `/api/tasks?${params.toString()}`
      )

      setTasks(response.tasks || [])
    } catch (err: any) {
      console.error("Failed to fetch tasks:", err)
      const errorMessage = err.message || "Failed to load tasks"
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    // Reset view mode when switching status
    if (currentStatus !== "active") {
      setViewMode("list")
    }
    fetchTasks()
  }, [currentStatus, selectedQuadrant])

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchTasks()
  }

  const handleTaskUpdate = (updatedTask: Task) => {
    // If we are in "active" view and task becomes "completed" or "deleted", remove it
    if (currentStatus === "active" && updatedTask.status !== "active") {
      setTasks(prev => prev.filter(t => t.id !== updatedTask.id))
      return
    }

    // If we are in "completed" view and task becomes "active" (uncheck), remove it
    if (currentStatus === "completed" && updatedTask.status !== "completed") {
      setTasks(prev => prev.filter(t => t.id !== updatedTask.id))
      return
    }

    // If we are in "deleted" view and task is restored (status change), remove it
    if (currentStatus === "deleted" && updatedTask.status !== "deleted") {
      setTasks(prev => prev.filter(t => t.id !== updatedTask.id))
      return
    }

    // Otherwise update in place
    setTasks(prev => prev.map(t => t.id === updatedTask.id ? updatedTask : t))
  }

  const handleTaskDelete = (taskId: number) => {
    // Optimistic update
    setTasks(prev => prev.filter(t => t.id !== taskId))
  }

  if (loading && !refreshing) {
    return (
      <div className="space-y-6">
        <div className="mb-6">
          <Skeleton className="h-32 w-full" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-80 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {error}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            className="ml-4"
          >
            <RefreshCw className="h-3 w-3 mr-2" />
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with Status Tabs and Refresh */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          {/* Title or similar if needed */}
        </div>

        <Tabs value={currentStatus} onValueChange={(v) => { setCurrentStatus(v as TaskStatus); setSelectedQuadrant(null); }} className="w-full md:w-auto">
          <TabsList className="grid w-full grid-cols-3 md:w-[400px]">
            <TabsTrigger value="active" className="flex items-center gap-2">
              <Layers className="h-4 w-4" /> Active
            </TabsTrigger>
            <TabsTrigger value="completed" className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" /> Done
            </TabsTrigger>
            <TabsTrigger value="deleted" className="flex items-center gap-2">
              <Trash2 className="h-4 w-4" /> Bin
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          className="w-full md:w-auto"
        >
          <RefreshCw
            className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {currentStatus === "active" ? (
        <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as "matrix" | "list")} className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-foreground">Active Tasks</h2>
              <p className="text-sm text-muted-foreground mt-1">
                {tasks.length} task{tasks.length !== 1 ? "s" : ""}
              </p>
            </div>
            <TabsList>
              <TabsTrigger value="matrix" className="flex items-center gap-2">
                <LayoutGrid className="h-4 w-4" />
                Matrix
              </TabsTrigger>
              <TabsTrigger value="list" className="flex items-center gap-2">
                <List className="h-4 w-4" />
                List
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="matrix" className="mt-6">
            <EisenhowerMatrix tasks={tasks} onTasksUpdate={setTasks} refresh={handleRefresh} />
          </TabsContent>

          <TabsContent value="list" className="mt-6 space-y-6">
            <QuadrantFilter
              selectedQuadrant={selectedQuadrant}
              onQuadrantChange={setSelectedQuadrant}
              taskCounts={taskCounts}
            />

            {tasks.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400">
                  No active tasks found.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {tasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    onUpdate={handleTaskUpdate}
                    onDelete={handleTaskDelete}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      ) : (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-foreground capitalize">{currentStatus} Tasks</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {tasks.length} task{tasks.length !== 1 ? "s" : ""}
            </p>
          </div>

          {tasks.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400">
                No {currentStatus} tasks.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onUpdate={handleTaskUpdate}
                  onDelete={handleTaskDelete}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
