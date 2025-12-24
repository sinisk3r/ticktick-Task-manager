"use client"

import * as React from "react"
import { DatePickerWithOptionalTime } from "@/components/DatePickerWithOptionalTime"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

interface DeadlinePickerProps {
    value?: string | null
    onChange: (date: string | null) => void
    allDay?: boolean
    onAllDayChange?: (allDay: boolean) => void
    placeholder?: string
    disabled?: boolean
}

export function DeadlinePicker({
    value,
    onChange,
    allDay = false,
    onAllDayChange,
    placeholder = "Pick a date",
    disabled
}: DeadlinePickerProps) {
    const handleAllDayChange = (checked: boolean) => {
        if (onAllDayChange) {
            onAllDayChange(checked)
        }

        // When switching to all-day, clear time component
        if (checked && value) {
            const date = new Date(value)
            date.setHours(0, 0, 0, 0)
            onChange(date.toISOString())
        }
        // When switching from all-day, default to 09:00 if no time exists
        else if (!checked && value) {
            const date = new Date(value)
            // Only set default time if it's currently midnight
            if (date.getHours() === 0 && date.getMinutes() === 0) {
                date.setHours(9, 0, 0, 0)
                onChange(date.toISOString())
            }
        }
    }

    const handleDateChange = (date: string | null) => {
        // If all-day is enabled, ensure time is set to 00:00:00
        if (allDay && date) {
            const d = new Date(date)
            d.setHours(0, 0, 0, 0)
            onChange(d.toISOString())
        } else {
            onChange(date)
        }
    }

    return (
        <div className="space-y-3">
            <DatePickerWithOptionalTime
                value={value}
                onChange={handleDateChange}
                placeholder={placeholder}
                disabled={disabled}
            />
            {onAllDayChange && (
                <div className="flex items-center justify-between">
                    <Label htmlFor="all-day-toggle" className="text-sm font-normal cursor-pointer">
                        All Day
                    </Label>
                    <Switch
                        id="all-day-toggle"
                        checked={allDay}
                        onCheckedChange={handleAllDayChange}
                        disabled={disabled}
                    />
                </div>
            )}
        </div>
    )
}

