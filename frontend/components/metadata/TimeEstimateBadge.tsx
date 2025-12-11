"use client"

import { Badge } from "@/components/ui/badge"
import { formatMinutes } from "./time"

interface TimeEstimateBadgeProps {
  minutes?: number | null
}

export function TimeEstimateBadge({ minutes }: TimeEstimateBadgeProps) {
  if (minutes === undefined || minutes === null) return null
  return (
    <Badge variant="outline" className="text-xs">
      ⏱️ {formatMinutes(minutes)}
    </Badge>
  )
}

