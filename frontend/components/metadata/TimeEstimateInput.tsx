"use client"

import { useEffect, useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { formatMinutes } from "./time"

interface TimeEstimateInputProps {
  value?: number | null
  onChange?: (minutes: number | null) => void
}

const QUICK_PRESETS = [15, 30, 60, 120]

export function TimeEstimateInput({ value, onChange }: TimeEstimateInputProps) {
  const [localValue, setLocalValue] = useState<string>(value?.toString() ?? "")

  useEffect(() => {
    setLocalValue(value?.toString() ?? "")
  }, [value])

  const handleBlur = () => {
    if (localValue.trim() === "") {
      onChange?.(null)
      return
    }
    const next = Number(localValue)
    if (Number.isNaN(next) || next < 0) {
      onChange?.(null)
      setLocalValue("")
      return
    }
    onChange?.(Math.floor(next))
  }

  const applyPreset = (preset: number) => {
    setLocalValue(preset.toString())
    onChange?.(preset)
  }

  return (
    <div className="space-y-2">
      <Input
        type="number"
        min={0}
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        onBlur={handleBlur}
        placeholder="Minutes (e.g., 90)"
      />
      <div className="flex flex-wrap gap-2">
        {QUICK_PRESETS.map((preset) => (
          <Button
            key={preset}
            type="button"
            variant="outline"
            size="sm"
            onClick={() => applyPreset(preset)}
          >
            {formatMinutes(preset)}
          </Button>
        ))}
      </div>
    </div>
  )
}

