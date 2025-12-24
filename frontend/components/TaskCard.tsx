"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TaskDetailPopover } from "@/components/TaskDetailPopover"
import { ChevronDown, ChevronUp, CheckCircle2, Calendar as CalendarIcon, Folder, Clock } from "lucide-react"
import { Task } from "@/types/task"
import { RepeatBadge } from "@/components/metadata/RepeatBadge"
import { TimeEstimateBadge } from "@/components/metadata/TimeEstimateBadge"
import { formatMinutes } from "@/components/metadata/time"
import { formatReminderMinutes, formatSmartDate } from "@/lib/dateUtils"
import { DescriptionPreview } from "@/components/DescriptionPreview"
import { motion } from "framer-motion"
import { format, isToday, isTomorrow, isPast } from "date-fns"

interface TaskCardProps {
  task: Task
  onUpdate?: (task: Task) => void
  onDelete?: (taskId: number) => void
  onToggleStatus?: (task: Task) => void
}

const getQuadrantConfig = (quadrant: string) => {
  const configs = {
    Q1: {
      label: "Q1: Urgent & Important",
      leftBorderColor: "border-l-red-500",
      badgeVariant: "destructive" as const,
      icon: "🔴",
    },
    Q2: {
      label: "Q2: Not Urgent, Important",
      leftBorderColor: "border-l-green-500",
      badgeVariant: "default" as const,
      icon: "🟢",
    },
    Q3: {
      label: "Q3: Urgent, Not Important",
      leftBorderColor: "border-l-yellow-500",
      badgeVariant: "secondary" as const,
      icon: "🟡",
    },
    Q4: {
      label: "Q4: Neither",
      leftBorderColor: "border-l-blue-500",
      badgeVariant: "outline" as const,
      icon: "🔵",
    },
  }
  return configs[quadrant as keyof typeof configs] || configs.Q4
}

export function TaskCard({ task, onUpdate, onDelete, onToggleStatus }: TaskCardProps) {
  const [expanded, setExpanded] = useState(false)
  const effectiveQuadrant =
    task.manual_quadrant_override || task.effective_quadrant || task.eisenhower_quadrant || "Q4"
  const quadrantConfig = getQuadrantConfig(effectiveQuadrant)
  const manualOverride = Boolean(task.manual_quadrant_override)
  const isCompleted = task.status === "completed"

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

  const priorityLabel = (priority?: number) => {
    if (priority === 5) return "High"
    if (priority === 3) return "Medium"
    if (priority === 1) return "Low"
    return null
  }

  const formatDate = (value?: string | null) => {
    if (!value) return ""
    const date = new Date(value)
    return date.toLocaleDateString()
  }

  return (
    <TaskDetailPopover
      task={task}
      onUpdate={onUpdate}
      onDelete={onDelete}
      trigger={
        <Card
          className={`p-4 border-l-4 ${quadrantConfig.leftBorderColor} transition-all hover:shadow-lg cursor-pointer`}
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

            {/* Task Title + status toggle */}
            <div className="flex items-start gap-2">
              <Button
                variant={isCompleted ? "secondary" : "ghost"}
                size="icon"
                className="h-7 w-7 shrink-0"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  onToggleStatus?.(task)
                }}
              >
                <CheckCircle2 className={`h-4 w-4 ${isCompleted ? "text-primary" : "text-muted-foreground"}`} />
              </Button>
              <div className="flex-1">
                <div className="relative inline-block">
                  <h3 className={`text-lg font-semibold mb-1 ${isCompleted ? "text-muted-foreground" : "text-foreground"}`}>
                    {task.title}
                  </h3>
                  <motion.div
                    initial={false}
                    animate={{ width: isCompleted ? "100%" : "0%" }}
                    transition={{ duration: 0.4, ease: "easeInOut" }}
                    className="absolute top-[14px] left-0 h-[2px] bg-primary/60 pointer-events-none"
                    style={{ transformOrigin: "left center" }}
                  />
                </div>

                {/* Task Description */}
                <p className="text-sm text-muted-foreground mb-2">{truncatedDescription}</p>

                {/* Description Preview with Checkboxes */}
                {task.description && (
                  <div className="mt-2">
                    <DescriptionPreview markdown={task.description} maxLines={2} />
                  </div>
                )}
              </div>
            </div>


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
              <div className="flex flex-wrap gap-1 justify-end">
                {manualOverride && (
                  <Badge variant="outline" className="text-[10px]">
                    {task.manual_override_at
                      ? `Updated ${new Date(task.manual_override_at).toLocaleDateString()}`
                      : "Manual"}
                  </Badge>
                )}
                {task.ticktick_task_id && (
                  <Badge variant="outline" className="text-xs">
                    TickTick
                  </Badge>
                )}
              </div>
            </div>

            {/* Metadata badges */}
            <div className="flex flex-wrap gap-2 mt-3">
              {/* Due date with time */}
              {task.due_date && (() => {
                const dueDate = new Date(task.due_date)
                const hasTime = dueDate.getHours() !== 0 || dueDate.getMinutes() !== 0
                const isOverdue = isPast(dueDate) && !isToday(dueDate)
                const dueDateText = isToday(dueDate) ? "Today" : isTomorrow(dueDate) ? "Tomorrow" : format(dueDate, "MMM d")

                return (
                  <Badge
                    variant={isOverdue ? "destructive" : isToday(dueDate) ? "default" : "outline"}
                    className="text-xs gap-1"
                  >
                    <CalendarIcon className="size-3" />
                    {dueDateText}
                    {hasTime && (
                      <span className="opacity-70 ml-0.5">
                        {format(dueDate, "h:mm a")}
                      </span>
                    )}
                  </Badge>
                )
              })()}

              {/* Project */}
              {task.project_name && (
                <Badge variant="outline" className="text-xs gap-1">
                  <Folder className="size-3" />
                  {task.project_name}
                </Badge>
              )}

              {/* Time estimate */}
              {typeof task.time_estimate === "number" && (
                <Badge variant="secondary" className="text-xs gap-1">
                  <Clock className="size-3" />
                  {formatMinutes(task.time_estimate)}
                </Badge>
              )}

              {/* Other metadata */}
              {priorityLabel(task.ticktick_priority) && (
                <Badge variant="secondary" className="text-xs">
                  ⭐ {priorityLabel(task.ticktick_priority)}
                </Badge>
              )}
              {task.start_date && (
                <Badge variant="outline" className="text-xs">
                  🏁 Start {formatDate(task.start_date)}
                </Badge>
              )}
              {/* Display reminders from new array */}
              {task.reminders && task.reminders.length > 0 && (
                <Badge variant="outline" className="text-xs">
                  🔔 {task.reminders.length === 1
                    ? formatReminderMinutes(task.reminders[0], task.all_day)
                    : `${task.reminders.length} reminders`}
                </Badge>
              )}
              {/* Fallback for old data: show reminder_time if no reminders array */}
              {!task.reminders?.length && task.reminder_time && (
                <Badge variant="outline" className="text-xs">
                  🔔 {formatSmartDate(task.reminder_time, true)}
                </Badge>
              )}
              {task.repeat_flag && <RepeatBadge pattern={task.repeat_flag} />}
              {task.ticktick_tags?.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  #{tag}
                </Badge>
              ))}
              {task.focus_time ? (
                <Badge variant="outline" className="text-xs">
                  🎯 {formatMinutes(task.focus_time)}
                </Badge>
              ) : null}
            </div>
          </Card>
      }
    />
  )
}
