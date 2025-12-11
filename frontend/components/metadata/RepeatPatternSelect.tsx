"use client"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface RepeatPatternSelectProps {
  value?: string | null
  onChange?: (pattern: string | null) => void
}

const options = [
  { label: "None", value: "none" },
  { label: "Daily", value: "RRULE:FREQ=DAILY" },
  { label: "Weekly", value: "RRULE:FREQ=WEEKLY" },
  { label: "Monthly", value: "RRULE:FREQ=MONTHLY" },
  { label: "Yearly", value: "RRULE:FREQ=YEARLY" },
]

export function RepeatPatternSelect({ value, onChange }: RepeatPatternSelectProps) {
  const current = value || "none"

  const handleChange = (val: string) => {
    if (val === "none") {
      onChange?.(null)
    } else {
      onChange?.(val)
    }
  }

  return (
    <Select value={current} onValueChange={handleChange}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Repeat" />
      </SelectTrigger>
      <SelectContent align="start">
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

