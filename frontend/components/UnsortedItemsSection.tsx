"use client"

import { useState } from "react"
import useSWR, { mutate } from "swr"
import { toast } from "sonner"
import { motion, AnimatePresence } from "framer-motion"
import { TaskDetailPopover } from "./TaskDetailPopover"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { API_BASE } from "@/lib/api"
import { Task } from "@/types/task"
import { Sparkles, Loader2 } from "lucide-react"

const fetcher = (url: string) => fetch(url).then((r) => r.json())

interface UnsortedItemsSectionProps {
  onTaskSorted?: (taskId: number, quadrant: string) => void
  onRefresh?: () => Promise<void>
  activeId?: number | null // To pause fetching during drag
}

export function UnsortedItemsSection({
  onTaskSorted,
  onRefresh,
  activeId
}: UnsortedItemsSectionProps) {
  const { data, isLoading } = useSWR(
    activeId ? null : `${API_BASE}/api/tasks/unsorted?user_id=1`, // Pause during drag
    fetcher,
    { refreshInterval: 10000 } // Reduced from 5s to avoid performance issues
  )

  const [assigningTask, setAssigningTask] = useState<number | null>(null)
  const [analyzingTask, setAnalyzingTask] = useState<number | null>(null)

  // Filter out completed/deleted tasks - only show active unsorted tasks
  const tasks = (data?.tasks || []).filter((task: Task) => task.status === 'active')

  const handleQuadrantAssign = async (taskId: number, quadrant: string) => {
    setAssigningTask(taskId)
    try {
      // Use existing /sort endpoint
      const response = await fetch(`${API_BASE}/api/tasks/${taskId}/sort`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quadrant }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error("Sort API error:", errorText)
        throw new Error(`Failed to assign quadrant: ${response.status}`)
      }

      // Refresh both views using SWR mutate (wait for completion)
      await Promise.all([
        mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`),
        mutate(`${API_BASE}/api/tasks?user_id=1`)
      ])

      // Notify parent component to refresh matrix
      onTaskSorted?.(taskId, quadrant)

      toast.success(`Task assigned to ${quadrant}`, { duration: 2000 })
    } catch (err: any) {
      console.error("Failed to assign quadrant:", err)
      toast.error(err.message || "Failed to assign quadrant. Please try again.")
    } finally {
      setAssigningTask(null)
    }
  }

  const handleAnalyze = async (taskId: number) => {
    setAnalyzingTask(taskId)
    try {
      const response = await fetch(`${API_BASE}/api/tasks/${taskId}/analyze`, {
        method: "POST",
      })

      if (!response.ok) {
        throw new Error("Analysis failed")
      }

      // Refresh the unsorted list
      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`)
      toast.success("Task analyzed successfully")
    } catch (error) {
      console.error("Analysis failed:", error)
      toast.error("Failed to analyze task")
    } finally {
      setAnalyzingTask(null)
    }
  }

  const priorityLabel = (priority: number) => {
    const labels: { [key: number]: string } = {
      0: "None",
      1: "Low",
      3: "Medium",
      5: "High",
    }
    return labels[priority] || "None"
  }

  if (isLoading && tasks.length === 0) {
    return (
      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-4">Unsorted Tasks</h2>
        <div className="flex gap-4">
          <Card className="flex-1 p-4 animate-pulse bg-card/50">
            <div className="h-20 bg-muted rounded"></div>
          </Card>
        </div>
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-4">Unsorted Tasks</h2>
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">
            No unsorted tasks. All tasks are organized!
          </p>
        </Card>
      </div>
    )
  }

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">
          Unsorted Tasks
          <Badge variant="secondary" className="ml-2">
            {tasks.length}
          </Badge>
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <AnimatePresence mode="popLayout">
          {tasks.map((task: Task) => (
            <motion.div
              key={task.id}
              layout
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.2 }}
            >
              <Card className="p-4 hover:shadow-md transition-shadow">
                <div className="mb-3">
                  <TaskDetailPopover
                    task={task}
                    onUpdate={async (updatedTask) => {
                      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`)
                    }}
                    onDelete={async (taskId) => {
                      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`)
                    }}
                    trigger={
                      <h3 className="text-sm font-semibold text-foreground mb-1 cursor-pointer hover:text-primary transition-colors line-clamp-2">
                        {task.title}
                      </h3>
                    }
                  />
                  {task.description && (
                    <p className="text-muted-foreground text-xs mb-2 line-clamp-2">
                      {task.description}
                    </p>
                  )}
                  <div className="flex gap-1.5 flex-wrap">
                    {(task.ticktick_priority ?? 0) > 0 && (
                      <Badge variant="secondary" className="text-xs">
                        Priority: {priorityLabel(task.ticktick_priority ?? 0)}
                      </Badge>
                    )}
                    {task.project_name && (
                      <Badge variant="outline" className="text-xs">
                        {task.project_name}
                      </Badge>
                    )}
                    {task.eisenhower_quadrant && (
                      <Badge variant="default" className="text-xs bg-blue-500/20 text-blue-300 border-blue-500/30">
                        AI suggests: {task.eisenhower_quadrant}
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Analyze Button */}
                <div className="mb-3">
                  <Button
                    onClick={() => handleAnalyze(task.id)}
                    disabled={analyzingTask === task.id}
                    size="sm"
                    variant="secondary"
                    className="w-full"
                  >
                    {analyzingTask === task.id ? (
                      <>
                        <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3 h-3 mr-1.5" />
                        Analyze with AI
                      </>
                    )}
                  </Button>
                </div>

                {/* Quadrant Assignment Buttons */}
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleQuadrantAssign(task.id, 'Q1')}
                    disabled={assigningTask === task.id}
                    className="flex-1 bg-red-500/10 hover:bg-red-500/20 border-red-500/30 text-red-300 hover:text-red-200"
                  >
                    {assigningTask === task.id ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <>
                        <span className="mr-1">🔴</span> Q1
                      </>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleQuadrantAssign(task.id, 'Q2')}
                    disabled={assigningTask === task.id}
                    className="flex-1 bg-green-500/10 hover:bg-green-500/20 border-green-500/30 text-green-300 hover:text-green-200"
                  >
                    {assigningTask === task.id ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <>
                        <span className="mr-1">🔵</span> Q2
                      </>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleQuadrantAssign(task.id, 'Q3')}
                    disabled={assigningTask === task.id}
                    className="flex-1 bg-yellow-500/10 hover:bg-yellow-500/20 border-yellow-500/30 text-yellow-300 hover:text-yellow-200"
                  >
                    {assigningTask === task.id ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <>
                        <span className="mr-1">🟡</span> Q3
                      </>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleQuadrantAssign(task.id, 'Q4')}
                    disabled={assigningTask === task.id}
                    className="flex-1 bg-gray-500/10 hover:bg-gray-500/20 border-gray-500/30 text-gray-300 hover:text-gray-200"
                  >
                    {assigningTask === task.id ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <>
                        <span className="mr-1">⚫</span> Q4
                      </>
                    )}
                  </Button>
                </div>
              </Card>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
