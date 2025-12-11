"use client"

import { Badge } from "@/components/ui/badge"

interface SubtaskIndicatorProps {
  completed?: number | null
  total?: number | null
}

export function SubtaskIndicator({ completed = 0, total = 0 }: SubtaskIndicatorProps) {
  if (!total) return null
  return (
    <Badge variant="secondary" className="text-xs">
      📋 {completed}/{total}
    </Badge>
  )
}

