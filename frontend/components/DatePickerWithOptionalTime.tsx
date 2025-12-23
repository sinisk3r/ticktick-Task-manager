"use client"

import * as React from "react"
import { format, isValid } from "date-fns"
import { Calendar as CalendarIcon, Clock, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import { Input } from "@/components/ui/input"

interface DatePickerWithOptionalTimeProps {
    value?: string | null
    onChange: (date: string | null) => void
    placeholder?: string
    disabled?: boolean
}

export function DatePickerWithOptionalTime({
    value,
    onChange,
    placeholder = "Pick a date",
    disabled
}: DatePickerWithOptionalTimeProps) {
    const [date, setDate] = React.useState<Date | undefined>(
        value ? new Date(value) : undefined
    )
    const [time, setTime] = React.useState<string>("")
    const [showTimePicker, setShowTimePicker] = React.useState(false)
    const [open, setOpen] = React.useState(false)

    // Check if the value has a time component (not midnight)
    const hasTimeComponent = (dateStr: string | null | undefined): boolean => {
        if (!dateStr) return false
        const d = new Date(dateStr)
        return d.getHours() !== 0 || d.getMinutes() !== 0
    }

    // Initialize state from value
    React.useEffect(() => {
        if (value) {
            const d = new Date(value)
            if (isValid(d)) {
                setDate(d)
                const hasTime = hasTimeComponent(value)
                setShowTimePicker(hasTime)
                if (hasTime) {
                    setTime(format(d, "HH:mm"))
                }
            }
        } else {
            setDate(undefined)
            setShowTimePicker(false)
            setTime("")
        }
    }, [value])

    const handleDateSelect = (newDate: Date | undefined) => {
        if (!newDate) {
            // Clearing date clears everything
            onChange(null)
            setDate(undefined)
            setShowTimePicker(false)
            setTime("")
            return
        }

        // If time picker is visible and has time, use it
        if (showTimePicker && time) {
            const [hours, minutes] = time.split(":").map(Number)
            newDate.setHours(hours || 0)
            newDate.setMinutes(minutes || 0)
        } else {
            // Date only - set to start of day
            newDate.setHours(0, 0, 0, 0)
        }

        setDate(newDate)
        onChange(newDate.toISOString())
    }

    const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newTime = e.target.value
        setTime(newTime)

        if (date && newTime) {
            const [hours, minutes] = newTime.split(":").map(Number)
            const newDate = new Date(date)
            newDate.setHours(hours || 0)
            newDate.setMinutes(minutes || 0)
            onChange(newDate.toISOString())
        }
    }

    const handleAddTime = () => {
        setShowTimePicker(true)
        // Default to current time or 9:00 AM
        const defaultTime = "09:00"
        setTime(defaultTime)

        if (date) {
            const [hours, minutes] = defaultTime.split(":").map(Number)
            const newDate = new Date(date)
            newDate.setHours(hours)
            newDate.setMinutes(minutes)
            onChange(newDate.toISOString())
        }
    }

    const handleTimePreset = (preset: string) => {
        setTime(preset)
        if (date) {
            const [hours, minutes] = preset.split(":").map(Number)
            const newDate = new Date(date)
            newDate.setHours(hours)
            newDate.setMinutes(minutes)
            onChange(newDate.toISOString())
        }
    }

    const handleNow = () => {
        const now = new Date()
        setDate(now)
        setTime(format(now, "HH:mm"))
        setShowTimePicker(true)
        onChange(now.toISOString())
    }

    const handleClear = (e: React.MouseEvent) => {
        e.stopPropagation()
        onChange(null)
        setDate(undefined)
        setShowTimePicker(false)
        setTime("")
        setOpen(false)
    }

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant={"outline"}
                    className={cn(
                        "w-full justify-start text-left font-normal h-9 px-3",
                        !date && "text-muted-foreground"
                    )}
                    disabled={disabled}
                >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {date ? (
                        <span className="flex items-center gap-2">
                            {format(date, "PPP")}
                            {showTimePicker && time && (
                                <span className="text-xs opacity-70 bg-muted px-1 rounded flex items-center gap-0.5">
                                    <Clock className="size-3" />
                                    {format(date, "p")}
                                </span>
                            )}
                        </span>
                    ) : (
                        <span>{placeholder}</span>
                    )}
                    {date && (
                        <X
                            className="ml-auto h-4 w-4 opacity-50 hover:opacity-100"
                            onClick={handleClear}
                        />
                    )}
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0 z-[120]" align="start">
                <Calendar
                    mode="single"
                    selected={date}
                    onSelect={handleDateSelect}
                    initialFocus
                />

                {/* Time controls section */}
                <div className="p-3 border-t">
                    {!showTimePicker ? (
                        <div className="space-y-2">
                            <Button
                                size="sm"
                                variant="ghost"
                                className="w-full gap-2"
                                onClick={handleAddTime}
                            >
                                <Clock className="size-4" />
                                Add time
                            </Button>
                        </div>
                    ) : (
                        <div className="space-y-3 animate-in slide-in-from-top-2">
                            <h4 className="font-medium text-xs text-muted-foreground flex items-center gap-2">
                                <Clock className="size-3" /> Time
                            </h4>
                            <Input
                                type="time"
                                value={time}
                                onChange={handleTimeChange}
                                className="h-8"
                            />
                            <div className="flex gap-1">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="flex-1 text-xs h-7"
                                    onClick={() => handleTimePreset("09:00")}
                                >
                                    Morning
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="flex-1 text-xs h-7"
                                    onClick={() => handleTimePreset("14:00")}
                                >
                                    Afternoon
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="flex-1 text-xs h-7"
                                    onClick={() => handleTimePreset("18:00")}
                                >
                                    Evening
                                </Button>
                            </div>
                        </div>
                    )}

                    {/* Quick actions */}
                    <div className="flex gap-2 mt-3 pt-3 border-t">
                        <Button
                            size="sm"
                            variant="ghost"
                            className="flex-1 text-xs"
                            onClick={handleNow}
                        >
                            Now
                        </Button>
                        {showTimePicker && (
                            <Button
                                size="sm"
                                variant="ghost"
                                className="flex-1 text-xs"
                                onClick={() => {
                                    setShowTimePicker(false)
                                    setTime("")
                                    if (date) {
                                        const newDate = new Date(date)
                                        newDate.setHours(0, 0, 0, 0)
                                        onChange(newDate.toISOString())
                                    }
                                }}
                            >
                                Remove time
                            </Button>
                        )}
                    </div>
                </div>
            </PopoverContent>
        </Popover>
    )
}
