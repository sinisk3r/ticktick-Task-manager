"use client"

import { useState, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import useSWR, { mutate } from "swr"
import { TaskDetailPopover } from "@/components/TaskDetailPopover"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Search, Plus, AlertCircle, Star, Trash2 } from "lucide-react"
import { DialogTrigger } from "@/components/ui/dialog"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { format, isToday, isThisWeek, isPast } from "date-fns"
import { Task, TasksResponse } from "@/types/task"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const fetcher = (url: string) => fetch(url).then((r) => r.json())

export default function ListView() {
  const [sortBy, setSortBy] = useState("due_date")
  const [filterBy, setFilterBy] = useState("all")
  const [groupBy, setGroupBy] = useState("none")
  const [searchQuery, setSearchQuery] = useState("")

  // Fetch tasks
  const { data, error, isLoading } = useSWR<TasksResponse>(
    `${API_BASE}/api/tasks?user_id=1&status=active&limit=200`,
    fetcher,
    { refreshInterval: 10000 }
  )

  const tasks = data?.tasks || []

  // Get effective quadrant
  const getQuadrant = (task: Task) =>
    task.manual_quadrant_override || task.effective_quadrant || task.eisenhower_quadrant

  // Get priority label
  const getPriorityLabel = (priority: number) => {
    const labels: { [key: number]: string } = {
      0: "None",
      1: "Low",
      3: "Medium",
      5: "High",
    }
    return labels[priority] || "None"
  }

  // Check if overdue
  const isOverdue = (dueDate: string | null | undefined) => {
    if (!dueDate) return false
    return isPast(new Date(dueDate)) && !isToday(new Date(dueDate))
  }

  // Format due date
  const formatDueDate = (dueDate: string | null | undefined) => {
    if (!dueDate) return null
    const date = new Date(dueDate)
    if (isToday(date)) return "Today"
    if (isThisWeek(date)) return format(date, "EEE")
    return format(date, "MMM d")
  }

  // Process tasks (filter, sort, group)
  const processedTasks = useMemo(() => {
    let filtered = tasks

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (t) =>
          t.title.toLowerCase().includes(query) ||
          t.description?.toLowerCase().includes(query) ||
          t.project_name?.toLowerCase().includes(query)
      )
    }

    // Apply time/quadrant filter
    if (filterBy === "today") {
      filtered = filtered.filter((t) => t.due_date && isToday(new Date(t.due_date)))
    } else if (filterBy === "week") {
      filtered = filtered.filter((t) => t.due_date && isThisWeek(new Date(t.due_date)))
    } else if (filterBy === "overdue") {
      filtered = filtered.filter((t) => isOverdue(t.due_date))
    } else if (filterBy.startsWith("Q")) {
      filtered = filtered.filter((t) => getQuadrant(t) === filterBy)
    }

    // Apply sorting
    filtered = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case "due_date":
          if (!a.due_date && !b.due_date) return 0
          if (!a.due_date) return 1
          if (!b.due_date) return -1
          return new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
        case "priority":
          return (b.ticktick_priority || 0) - (a.ticktick_priority || 0)
        case "created":
          return (
            new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
          )
        case "title":
          return a.title.localeCompare(b.title)
        default:
          return 0
      }
    })

    // Apply grouping
    if (groupBy === "none") {
      return [{ title: "All Tasks", tasks: filtered }]
    } else if (groupBy === "project") {
      const groups: { [key: string]: Task[] } = {}
      filtered.forEach((task) => {
        const key = task.project_name || "No Project"
        if (!groups[key]) groups[key] = []
        groups[key].push(task)
      })
      return Object.entries(groups).map(([title, tasks]) => ({ title, tasks }))
    } else if (groupBy === "priority") {
      const groups: { [key: string]: Task[] } = {
        High: [],
        Medium: [],
        Low: [],
        None: [],
      }
      filtered.forEach((task) => {
        const priority = task.ticktick_priority || 0
        if (priority === 5) groups.High.push(task)
        else if (priority === 3) groups.Medium.push(task)
        else if (priority === 1) groups.Low.push(task)
        else groups.None.push(task)
      })
      return Object.entries(groups)
        .filter(([_, tasks]) => tasks.length > 0)
        .map(([title, tasks]) => ({ title, tasks }))
    } else if (groupBy === "due_date") {
      const groups: { [key: string]: Task[] } = {
        Overdue: [],
        Today: [],
        "This Week": [],
        Later: [],
        "No Due Date": [],
      }
      filtered.forEach((task) => {
        if (!task.due_date) {
          groups["No Due Date"].push(task)
        } else if (isOverdue(task.due_date)) {
          groups.Overdue.push(task)
        } else if (isToday(new Date(task.due_date))) {
          groups.Today.push(task)
        } else if (isThisWeek(new Date(task.due_date))) {
          groups["This Week"].push(task)
        } else {
          groups.Later.push(task)
        }
      })
      return Object.entries(groups)
        .filter(([_, tasks]) => tasks.length > 0)
        .map(([title, tasks]) => ({ title, tasks }))
    } else if (groupBy === "quadrant") {
      const groups: { [key: string]: Task[] } = {
        Q1: [],
        Q2: [],
        Q3: [],
        Q4: [],
      }
      filtered.forEach((task) => {
        const quadrant = getQuadrant(task)
        if (quadrant && groups[quadrant]) {
          groups[quadrant].push(task)
        }
      })
      return Object.entries(groups)
        .filter(([_, tasks]) => tasks.length > 0)
        .map(([title, tasks]) => ({ title, tasks }))
    }

    return [{ title: "All Tasks", tasks: filtered }]
  }, [tasks, searchQuery, filterBy, sortBy, groupBy])

  const handleTaskUpdate = (updatedTask: Task) => {
    // Optimistically update the cache
    mutate(
      `${API_BASE}/api/tasks?user_id=1&status=active&limit=200`,
      (current: TasksResponse | undefined) => {
        if (!current) return current
        return {
          ...current,
          tasks: current.tasks.map((t) => (t.id === updatedTask.id ? updatedTask : t)),
        }
      },
      false
    )
  }

  const handleTaskDelete = (taskId: number) => {
    // Optimistically update the cache
    mutate(
      `${API_BASE}/api/tasks?user_id=1&status=active&limit=200`,
      (current: TasksResponse | undefined) => {
        if (!current) return current
        return {
          ...current,
          tasks: current.tasks.filter((t) => t.id !== taskId),
          total: current.total - 1,
        }
      },
      false
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-16 w-full" />
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>Failed to load tasks. Please try again.</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">List View</h1>
        <p className="text-muted-foreground mt-2">
          Comprehensive task list with filtering, sorting, and grouping.
        </p>
      </div>

      {/* Toolbar */}
      <div className="bg-card p-4 rounded-lg border space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search tasks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Filters and Controls */}
        <div className="flex flex-wrap gap-3">
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="due_date">Sort: Due Date</SelectItem>
              <SelectItem value="priority">Sort: Priority</SelectItem>
              <SelectItem value="created">Sort: Created</SelectItem>
              <SelectItem value="title">Sort: Title</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterBy} onValueChange={setFilterBy}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Tasks</SelectItem>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="overdue">Overdue</SelectItem>
              <SelectItem value="Q1">Quadrant 1</SelectItem>
              <SelectItem value="Q2">Quadrant 2</SelectItem>
              <SelectItem value="Q3">Quadrant 3</SelectItem>
              <SelectItem value="Q4">Quadrant 4</SelectItem>
            </SelectContent>
          </Select>

          <Select value={groupBy} onValueChange={setGroupBy}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No Grouping</SelectItem>
              <SelectItem value="project">Group by Project</SelectItem>
              <SelectItem value="priority">Group by Priority</SelectItem>
              <SelectItem value="due_date">Group by Due Date</SelectItem>
              <SelectItem value="quadrant">Group by Quadrant</SelectItem>
            </SelectContent>
          </Select>

          <div className="ml-auto flex gap-2">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Task
            </Button>
          </div>
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-6">
        {processedTasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">
              No tasks found. Try adjusting your filters.
            </p>
          </div>
        ) : (
          processedTasks.map((group) => (
            <div key={group.title}>
              <h2 className="text-sm font-semibold text-muted-foreground mb-3">
                {group.title} ({group.tasks.length})
              </h2>

              <div className="space-y-2">
                <AnimatePresence mode="popLayout">
                  {group.tasks.map((task) => (
                    <motion.div
                      key={task.id}
                      layout
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
                    >
                      <TaskDetailPopover
                        task={task}
                        onUpdate={handleTaskUpdate}
                        onDelete={handleTaskDelete}
                        trigger={
                          <DialogTrigger asChild>
                            <TaskListItem task={task} />
                          </DialogTrigger>
                        }
                      />
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function TaskListItem({ task }: { task: Task }) {
  const getQuadrant = (task: Task) =>
    task.manual_quadrant_override || task.effective_quadrant || task.eisenhower_quadrant

  const getPriorityLabel = (priority: number) => {
    const labels: { [key: number]: string } = {
      0: "None",
      1: "Low",
      3: "Medium",
      5: "High",
    }
    return labels[priority] || "None"
  }

  const isOverdue = (dueDate: string | null | undefined) => {
    if (!dueDate) return false
    return isPast(new Date(dueDate)) && !isToday(new Date(dueDate))
  }

  const formatDueDate = (dueDate: string | null | undefined) => {
    if (!dueDate) return null
    const date = new Date(dueDate)
    if (isToday(date)) return "Today"
    if (isThisWeek(date)) return format(date, "EEE")
    return format(date, "MMM d")
  }

  return (
    <button className="group w-full flex items-center gap-3 p-4 bg-card rounded-lg border hover:border-primary cursor-pointer transition-all text-left">
      <Checkbox checked={task.status === "completed"} className="pointer-events-none" />

      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{task.title}</div>
        <div className="flex flex-wrap gap-2 mt-2">
          {task.project_name && (
            <Badge variant="outline" className="text-xs">
              {task.project_name}
            </Badge>
          )}
          {(task.ticktick_priority || 0) > 0 && (
            <Badge variant="secondary" className="text-xs">
              {getPriorityLabel(task.ticktick_priority || 0)}
            </Badge>
          )}
          {task.due_date && (
            <Badge
              variant={isOverdue(task.due_date) ? "destructive" : "default"}
              className="text-xs"
            >
              {formatDueDate(task.due_date)}
            </Badge>
          )}
          {getQuadrant(task) && (
            <Badge variant="outline" className="text-xs">
              {getQuadrant(task)}
            </Badge>
          )}
          {task.ticktick_tags?.map((tag) => (
            <Badge key={tag} variant="secondary" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      </div>

      <div className="opacity-0 group-hover:opacity-100 flex gap-1 transition-opacity">
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Star className="h-4 w-4" />
        </Button>
      </div>
    </button>
  )
}
