"use client"

import { Badge } from "@/components/ui/badge"

interface RepeatBadgeProps {
  pattern?: string | null
}

function describePattern(pattern?: string | null): string {
  if (!pattern) return ""
  const normalized = pattern.toUpperCase()
  if (normalized.includes("FREQ=DAILY")) return "Daily"
  if (normalized.includes("FREQ=WEEKLY")) return "Weekly"
  if (normalized.includes("FREQ=MONTHLY")) return "Monthly"
  if (normalized.includes("FREQ=YEARLY")) return "Yearly"
  return pattern
}

export function RepeatBadge({ pattern }: RepeatBadgeProps) {
  if (!pattern) return null
  return (
    <Badge variant="outline" className="text-xs">
      🔁 {describePattern(pattern)}
    </Badge>
  )
}

