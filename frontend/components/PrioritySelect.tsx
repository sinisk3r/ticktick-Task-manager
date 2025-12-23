"use client"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface PrioritySelectProps {
  value: number
  onChange: (value: number) => void
  disabled?: boolean
}

const PRIORITIES = [
  { value: 0, label: "None", color: "text-muted-foreground" },
  { value: 1, label: "Low", color: "text-blue-500" },
  { value: 3, label: "Medium", color: "text-yellow-500" },
  { value: 5, label: "High", color: "text-red-500" },
]

export function PrioritySelect({ value, onChange, disabled }: PrioritySelectProps) {
  const currentPriority = PRIORITIES.find((p) => p.value === value) || PRIORITIES[0]

  return (
    <Select
      value={String(value)}
      onValueChange={(val) => onChange(Number(val))}
      disabled={disabled}
    >
      <SelectTrigger className="w-full">
        <SelectValue>
          <span className={currentPriority.color}>{currentPriority.label}</span>
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="z-[120]">
        {PRIORITIES.map((priority) => (
          <SelectItem key={priority.value} value={String(priority.value)}>
            <span className={priority.color}>{priority.label}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
