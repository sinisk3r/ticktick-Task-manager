"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Progress } from "@/components/ui/progress"
import { api } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Task {
  id: number
  title: string
  description?: string
  urgency_score: number
  importance_score: number
  eisenhower_quadrant: string
  analysis_reasoning?: string
  status: string
  created_at: string
  ticktick_task_id?: string
}

interface TasksResponse {
  tasks: Task[]
  total: number
}

const QuadrantCard = ({
  title,
  description,
  tasks,
  bgColor,
  borderColor,
  icon,
}: {
  title: string
  description: string
  tasks: Task[]
  bgColor: string
  borderColor: string
  icon: string
}) => {
  return (
    <Card
      className={`p-6 ${bgColor} ${borderColor} border-2 h-full min-h-[300px] flex flex-col`}
    >
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">{icon}</span>
          <h3 className="text-lg font-bold text-gray-100">{title}</h3>
        </div>
        <p className="text-xs text-gray-400">{description}</p>
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
            <TaskPopover key={task.id} task={task} />
          ))
        )}
      </div>
    </Card>
  )
}

const TaskPopover = ({ task }: { task: Task }) => {
  const [expanded, setExpanded] = useState(false)

  const truncatedReasoning = task.analysis_reasoning
    ? task.analysis_reasoning.length > 120
      ? task.analysis_reasoning.substring(0, 120) + "..."
      : task.analysis_reasoning
    : "No AI analysis available"

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button className="w-full text-left p-3 rounded-lg bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700 transition-colors">
          <p className="text-sm font-medium text-gray-200 truncate">
            {task.title}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-gray-400">U: {task.urgency_score}</span>
            <span className="text-xs text-gray-400">I: {task.importance_score}</span>
          </div>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-96 bg-gray-800 border-gray-700" side="right">
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
            {task.ticktick_task_id && (
              <Badge variant="outline" className="text-xs">
                TickTick
              </Badge>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

export function EisenhowerMatrix() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTasks = async () => {
    try {
      setError(null)
      const params = new URLSearchParams({
        user_id: "1",
        status: "active",
        limit: "100",
      })

      const response = await api.get<TasksResponse>(
        `/api/tasks?${params.toString()}`
      )

      setTasks(response.tasks || [])
    } catch (err: any) {
      console.error("Failed to fetch tasks:", err)
      setError(err.message || "Failed to load tasks")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const q1Tasks = tasks.filter((t) => t.eisenhower_quadrant === "Q1")
  const q2Tasks = tasks.filter((t) => t.eisenhower_quadrant === "Q2")
  const q3Tasks = tasks.filter((t) => t.eisenhower_quadrant === "Q3")
  const q4Tasks = tasks.filter((t) => t.eisenhower_quadrant === "Q4")

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
      </div>

      {/* Matrix Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Q1: Urgent & Important (Top Left) */}
        <QuadrantCard
          title="Q1: Do First"
          description="Urgent & Important - Handle immediately"
          tasks={q1Tasks}
          bgColor="bg-red-900/20"
          borderColor="border-red-700"
          icon="🔴"
        />

        {/* Q2: Not Urgent, Important (Top Right) */}
        <QuadrantCard
          title="Q2: Schedule"
          description="Not Urgent, Important - Plan for later"
          tasks={q2Tasks}
          bgColor="bg-green-900/20"
          borderColor="border-green-700"
          icon="🟢"
        />

        {/* Q3: Urgent, Not Important (Bottom Left) */}
        <QuadrantCard
          title="Q3: Delegate"
          description="Urgent, Not Important - Consider delegating"
          tasks={q3Tasks}
          bgColor="bg-yellow-900/20"
          borderColor="border-yellow-700"
          icon="🟡"
        />

        {/* Q4: Neither (Bottom Right) */}
        <QuadrantCard
          title="Q4: Eliminate"
          description="Neither Urgent nor Important - Minimize time"
          tasks={q4Tasks}
          bgColor="bg-blue-900/20"
          borderColor="border-blue-700"
          icon="🔵"
        />
      </div>
    </div>
  )
}
