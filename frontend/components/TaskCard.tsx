"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp } from "lucide-react"

interface Task {
  id: number
  title: string
  description?: string
  urgency_score: number
  importance_score: number
  eisenhower_quadrant: string
  effective_quadrant?: string
  manual_quadrant_override?: string
  manual_override_reason?: string
  manual_override_at?: string
  analysis_reasoning?: string
  status: string
  created_at: string
  ticktick_task_id?: string
}

interface TaskCardProps {
  task: Task
}

const getQuadrantConfig = (quadrant: string) => {
  const configs = {
    Q1: {
      label: "Q1: Urgent & Important",
      bgColor: "bg-red-900/50",
      borderColor: "border-red-700",
      badgeVariant: "destructive" as const,
      icon: "🔴",
    },
    Q2: {
      label: "Q2: Not Urgent, Important",
      bgColor: "bg-green-900/50",
      borderColor: "border-green-700",
      badgeVariant: "default" as const,
      icon: "🟢",
    },
    Q3: {
      label: "Q3: Urgent, Not Important",
      bgColor: "bg-yellow-900/50",
      borderColor: "border-yellow-700",
      badgeVariant: "secondary" as const,
      icon: "🟡",
    },
    Q4: {
      label: "Q4: Neither",
      bgColor: "bg-blue-900/50",
      borderColor: "border-blue-700",
      badgeVariant: "outline" as const,
      icon: "🔵",
    },
  }
  return configs[quadrant as keyof typeof configs] || configs.Q4
}

export function TaskCard({ task }: TaskCardProps) {
  const [expanded, setExpanded] = useState(false)
  const effectiveQuadrant =
    task.manual_quadrant_override || task.effective_quadrant || task.eisenhower_quadrant
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
    <Card
      className={`p-4 border-2 ${quadrantConfig.borderColor} ${quadrantConfig.bgColor} transition-all hover:shadow-lg`}
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
      <h3 className="text-lg font-semibold mb-2 text-gray-100">
        {task.title}
      </h3>

      {/* Task Description */}
      <p className="text-sm text-gray-300 mb-4">{truncatedDescription}</p>

      {/* Urgency Score */}
      <div className="mb-3">
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-gray-400">Urgency</span>
          <span className="text-xs font-semibold text-gray-300">
            {task.urgency_score}/10
          </span>
        </div>
        <Progress value={task.urgency_score * 10} className="h-2" />
      </div>

      {/* Importance Score */}
      <div className="mb-4">
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
        <div className="flex items-start gap-2 mb-2">
          <span className="text-lg">💡</span>
          <div className="flex-1">
            <p className="text-xs text-gray-300 leading-relaxed">
              {expanded ? task.analysis_reasoning : truncatedReasoning}
            </p>
          </div>
        </div>

        {/* Expand/Collapse Button */}
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

      {/* Metadata Footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-700">
        <span className="text-xs text-gray-500">
          {new Date(task.created_at).toLocaleDateString()}
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
  )
}
