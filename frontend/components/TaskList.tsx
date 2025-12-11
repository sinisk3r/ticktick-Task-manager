"use client"

import { useState, useEffect } from "react"
import { TaskCard } from "./TaskCard"
import { QuadrantFilter } from "./QuadrantFilter"
import { EisenhowerMatrix } from "./EisenhowerMatrix"
import { api } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw, LayoutGrid, List } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

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
  status: string
  created_at: string
  ticktick_task_id?: string
}

interface TasksResponse {
  tasks: Task[]
  total: number
}

export function TaskList() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedQuadrant, setSelectedQuadrant] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const getQuadrant = (task: Task) =>
    task.manual_quadrant_override || task.effective_quadrant || task.eisenhower_quadrant

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
      setError(null)

      // Build query parameters
      const params = new URLSearchParams({
        user_id: "1", // Hardcoded for single-user mode
        status: "active",
        limit: "100",
      })

      if (selectedQuadrant) {
        params.append("quadrant", selectedQuadrant)
      }

      const response = await api.get<TasksResponse>(
        `/api/tasks?${params.toString()}`
      )

      setTasks(response.tasks || [])
    } catch (err: any) {
      console.error("Failed to fetch tasks:", err)
      setError(err.message || "Failed to load tasks")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [selectedQuadrant])

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchTasks()
  }

  // Filter tasks based on selected quadrant
  const filteredTasks = selectedQuadrant
    ? tasks.filter((task) => getQuadrant(task) === selectedQuadrant)
    : tasks

  if (loading) {
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

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">📋</div>
          <h3 className="text-xl font-semibold mb-2 text-gray-200">
            No tasks yet
          </h3>
          <p className="text-gray-400 mb-6">
            Sync your TickTick tasks from the Analyze tab to get started with
            AI-powered task prioritization.
          </p>
        </div>
      </div>
    )
  }

  return (
    <Tabs defaultValue="matrix" className="space-y-6">
      {/* Header with view toggle and refresh button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">My Tasks</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {tasks.length} task{tasks.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <div className="flex items-center gap-3">
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
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Matrix View */}
      <TabsContent value="matrix" className="mt-6">
        <EisenhowerMatrix tasks={tasks} onTasksUpdate={setTasks} refresh={handleRefresh} />
      </TabsContent>

      {/* List View */}
      <TabsContent value="list" className="mt-6 space-y-6">
        {/* Quadrant Filter */}
        <QuadrantFilter
          selectedQuadrant={selectedQuadrant}
          onQuadrantChange={setSelectedQuadrant}
          taskCounts={taskCounts}
        />

        {/* Task Cards Grid */}
        {filteredTasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-400">
              No tasks in {selectedQuadrant}. Try selecting a different quadrant.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTasks.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        )}
      </TabsContent>
    </Tabs>
  )
}
