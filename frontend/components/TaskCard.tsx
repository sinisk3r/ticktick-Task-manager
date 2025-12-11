"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { TaskDetailPopover } from "@/components/TaskDetailPopover"
import { DialogTrigger } from "@/components/ui/dialog"
import { ChevronDown, ChevronUp } from "lucide-react"
import { Task } from "@/types/task"

interface TaskCardProps {
  task: Task
  onUpdate?: (task: Task) => void
  onDelete?: (taskId: number) => void
}

const getQuadrantConfig = (quadrant: string) => {
  const configs = {
    Q1: {
      label: "Q1: Urgent & Important",
      bgColor: "bg-red-100 dark:bg-red-900/20",
      borderColor: "border-red-200 dark:border-red-800",
      badgeVariant: "destructive" as const,
      icon: "🔴",
    },
    Q2: {
      label: "Q2: Not Urgent, Important",
      bgColor: "bg-green-100 dark:bg-green-900/20",
      borderColor: "border-green-200 dark:border-green-800",
      badgeVariant: "default" as const,
      icon: "🟢",
    },
    Q3: {
      label: "Q3: Urgent, Not Important",
      bgColor: "bg-yellow-100 dark:bg-yellow-900/20",
      borderColor: "border-yellow-200 dark:border-yellow-800",
      badgeVariant: "secondary" as const,
      icon: "🟡",
    },
    Q4: {
      label: "Q4: Neither",
      bgColor: "bg-blue-100 dark:bg-blue-900/20",
      borderColor: "border-blue-200 dark:border-blue-800",
      badgeVariant: "outline" as const,
      icon: "🔵",
    },
  }
  return configs[quadrant as keyof typeof configs] || configs.Q4
}

export function TaskCard({ task, onUpdate, onDelete }: TaskCardProps) {
  const [expanded, setExpanded] = useState(false)
  const effectiveQuadrant =
    task.manual_quadrant_override || task.effective_quadrant || task.eisenhower_quadrant || "Q4"
  const quadrantConfig = getQuadrantConfig(effectiveQuadrant)
  const manualOverride = Boolean(task.manual_quadrant_override)

  // Truncate description to 100 characters
  const truncatedDescription = task.description
    ? task.description.length > 100
      ? task.description.substring(0, 100) + "..."
      : task.description
    : "No description"

  // Truncate reasoning for initial display
  const truncatedReasoning = task.analysis_reasoning
    ? task.analysis_reasoning.length > 120
      ? task.analysis_reasoning.substring(0, 120) + "..."
      : task.analysis_reasoning
    : "No AI analysis available"

  return (
    <TaskDetailPopover
      task={task}
      onUpdate={onUpdate}
      onDelete={onDelete}
      trigger={
        <DialogTrigger asChild>
          <Card
            className={`p-4 border-2 ${quadrantConfig.borderColor} ${quadrantConfig.bgColor} transition-all hover:shadow-lg cursor-pointer`}
          >
            {/* Quadrant Badge */}
            <div className="mb-3">
              <Badge variant={quadrantConfig.badgeVariant} className="text-sm">
                {quadrantConfig.icon} {quadrantConfig.label}
              </Badge>
              {manualOverride && (
                <Badge variant="outline" className="ml-2 text-xs">
                  Manual override
                </Badge>
              )}
            </div>

            {/* Task Title */}
            <h3 className="text-lg font-semibold mb-2 text-foreground">
              {task.title}
            </h3>

            {/* Task Description */}
            <p className="text-sm text-muted-foreground mb-4">{truncatedDescription}</p>

            {/* Urgency Score */}
            {task.urgency_score !== undefined && (
              <div className="mb-3">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-muted-foreground">Urgency</span>
                  <span className="text-xs font-semibold text-foreground">
                    {task.urgency_score}/10
                  </span>
                </div>
                <Progress value={task.urgency_score * 10} className="h-2" />
              </div>
            )}

            {/* Importance Score */}
            {task.importance_score !== undefined && (
              <div className="mb-4">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-muted-foreground">Importance</span>
                  <span className="text-xs font-semibold text-foreground">
                    {task.importance_score}/10
                  </span>
                </div>
                <Progress value={task.importance_score * 10} className="h-2" />
              </div>
            )}

            {/* AI Reasoning */}
            <div className="border-t border-border pt-3">
              <div className="flex items-start gap-2 mb-2">
                <span className="text-lg">💡</span>
                <div className="flex-1">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {expanded ? task.analysis_reasoning : truncatedReasoning}
                  </p>
                </div>
              </div>

              {/* Expand/Collapse Button */}
              {task.analysis_reasoning && task.analysis_reasoning.length > 120 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation()
                    setExpanded(!expanded)
                  }}
                  className="w-full mt-2 text-xs text-muted-foreground hover:text-foreground"
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

            {/* Metadata Footer */}
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-700">
              <span className="text-xs text-gray-500">
                {task.created_at ? new Date(task.created_at).toLocaleDateString() : ""}
              </span>
              {manualOverride && (
                <span className="text-[10px] text-gray-400">
                  {task.manual_override_at
                    ? `Updated ${new Date(task.manual_override_at).toLocaleDateString()}`
                    : "Manual"}
                </span>
              )}
              {task.ticktick_task_id && (
                <Badge variant="outline" className="text-xs">
                  TickTick
                </Badge>
              )}
            </div>
          </Card>
        </DialogTrigger>
      }
    />
  )
}
