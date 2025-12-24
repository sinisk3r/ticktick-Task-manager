"use client"

import * as React from "react"
import { format, isToday, isTomorrow, isValid, startOfMonth, addMonths, subMonths } from "date-fns"
import { Calendar as CalendarIcon, Clock, Bell, ChevronRight, ChevronDown, ChevronLeft, X, Circle } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Checkbox } from "@/components/ui/checkbox"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"

interface UnifiedDatePickerProps {
    // Date/time
    value?: string | null
    onChange: (date: string | null) => void

    // All-day flag
    allDay?: boolean
    onAllDayChange?: (allDay: boolean) => void

    // Reminders
    reminders?: number[]
    onRemindersChange?: (reminders: number[]) => void

    // Optional
    placeholder?: string
    disabled?: boolean
}

// Preset options for date-only (allDay=true)
const DATE_ONLY_PRESETS = [
    { label: "On the day", minutes: 0 },
    { label: "1 day early", minutes: 1440 },
    { label: "2 days early", minutes: 2880 },
    { label: "1 week early", minutes: 10080 },
]

// Preset options for date+time (allDay=false)
const DATE_TIME_PRESETS = [
    { label: "On time", minutes: 0 },
    { label: "5 min early", minutes: 5 },
    { label: "15 min early", minutes: 15 },
    { label: "30 min early", minutes: 30 },
    { label: "1 hour early", minutes: 60 },
    { label: "1 day early", minutes: 1440 },
]

export function UnifiedDatePicker({
    value,
    onChange,
    allDay = false,
    onAllDayChange,
    reminders = [],
    onRemindersChange,
    placeholder = "Set due date",
    disabled
}: UnifiedDatePickerProps) {
    const [open, setOpen] = React.useState(false)
    const [date, setDate] = React.useState<Date | undefined>(
        value ? new Date(value) : undefined
    )
    const [time, setTime] = React.useState<string>("")
    const [month, setMonth] = React.useState<Date>(value ? new Date(value) : new Date())

    // Collapsible section states
    const [timeExpanded, setTimeExpanded] = React.useState(false)
    const [reminderExpanded, setReminderExpanded] = React.useState(false)

    // Local state for reminders (saves on close)
    const [localReminders, setLocalReminders] = React.useState<number[]>(reminders)

    // Check if the value has a time component (not midnight)
    const hasTimeComponent = (dateStr: string | null | undefined): boolean => {
        if (!dateStr) return false
        const d = new Date(dateStr)
        return d.getHours() !== 0 || d.getMinutes() !== 0
    }

    // Initialize state from value prop
    React.useEffect(() => {
        if (value) {
            const d = new Date(value)
            if (isValid(d)) {
                setDate(d)
                setMonth(d)
                const hasTime = hasTimeComponent(value)
                if (hasTime) {
                    setTime(format(d, "HH:mm"))
                }
            }
        } else {
            setDate(undefined)
            setTime("")
        }
    }, [value])

    // Sync local reminders when prop changes
    React.useEffect(() => {
        setLocalReminders(reminders)
    }, [reminders])

    // Get preset options based on allDay flag
    const presets = allDay ? DATE_ONLY_PRESETS : DATE_TIME_PRESETS

    // Format smart date label for button
    const formatSmartDate = (d: Date, includeTime: boolean): string => {
        let dateStr: string
        if (isToday(d)) {
            dateStr = "Today"
        } else if (isTomorrow(d)) {
            dateStr = "Tomorrow"
        } else {
            dateStr = format(d, "MMM d")
        }

        if (includeTime && hasTimeComponent(d.toISOString())) {
            return `${dateStr}, ${format(d, "HH:mm")}`
        }
        return dateStr
    }

    // Format reminder minutes to human-readable
    const formatReminderMinutes = (minutes: number): string => {
        if (minutes === 0) return allDay ? "On the day" : "On time"
        if (minutes < 60) return `${minutes}m`
        if (minutes < 1440) return `${Math.floor(minutes / 60)}h`
        return `${Math.floor(minutes / 1440)}d`
    }

    // Handle date selection from calendar
    const handleDateSelect = (newDate: Date | undefined) => {
        if (!newDate) return

        // Preserve time if set
        if (time && !allDay) {
            const [hours, minutes] = time.split(":").map(Number)
            newDate.setHours(hours || 0)
            newDate.setMinutes(minutes || 0)
        } else {
            newDate.setHours(0, 0, 0, 0)
        }

        setDate(newDate)
    }

    // Handle time input change
    const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newTime = e.target.value
        setTime(newTime)

        if (date && newTime) {
            const [hours, minutes] = newTime.split(":").map(Number)
            const newDate = new Date(date)
            newDate.setHours(hours || 0)
            newDate.setMinutes(minutes || 0)
            setDate(newDate)
        }
    }

    // Handle time preset
    const handleTimePreset = (preset: string) => {
        setTime(preset)
        if (date) {
            const [hours, minutes] = preset.split(":").map(Number)
            const newDate = new Date(date)
            newDate.setHours(hours)
            newDate.setMinutes(minutes)
            setDate(newDate)
        }
    }

    // Handle reminder toggle
    const handleReminderToggle = (minutes: number, checked: boolean) => {
        let newReminders: number[]
        if (checked) {
            newReminders = [...localReminders, minutes].filter((v, i, arr) => arr.indexOf(v) === i)
        } else {
            newReminders = localReminders.filter(m => m !== minutes)
        }
        newReminders.sort((a, b) => a - b)
        setLocalReminders(newReminders)
    }

    // Handle all-day toggle
    const handleAllDayToggle = (checked: boolean) => {
        if (onAllDayChange) {
            onAllDayChange(checked)
        }

        if (checked && date) {
            // Clear time when switching to all-day
            const newDate = new Date(date)
            newDate.setHours(0, 0, 0, 0)
            setDate(newDate)
            setTime("")
        } else if (!checked && date && !time) {
            // Default to 09:00 when switching from all-day
            const newDate = new Date(date)
            newDate.setHours(9, 0, 0, 0)
            setDate(newDate)
            setTime("09:00")
        }
    }

    // Handle Clear
    const handleClear = (e: React.MouseEvent) => {
        e.stopPropagation()
        onChange(null)
        if (onRemindersChange) {
            onRemindersChange([])
        }
        setDate(undefined)
        setTime("")
        setLocalReminders([])
        setTimeExpanded(false)
        setReminderExpanded(false)
        setOpen(false)
    }

    // Auto-save on close
    const handleOpenChange = (newOpen: boolean) => {
        if (!newOpen && open) {
            // Save on close
            if (date) {
                onChange(date.toISOString())
            }
            if (onRemindersChange) {
                onRemindersChange(localReminders)
            }
        }
        setOpen(newOpen)
    }

    // Go to today
    const handleGoToToday = () => {
        const today = new Date()
        setMonth(today)
        // Also select today
        if (time && !allDay) {
            const [hours, minutes] = time.split(":").map(Number)
            today.setHours(hours || 0)
            today.setMinutes(minutes || 0)
        } else {
            today.setHours(0, 0, 0, 0)
        }
        setDate(today)
    }

    // Get reminder summary for collapsed state
    const getReminderSummary = (): string => {
        if (localReminders.length === 0) return "None"
        if (localReminders.length === 1) {
            const preset = presets.find(p => p.minutes === localReminders[0])
            return preset ? preset.label : formatReminderMinutes(localReminders[0])
        }
        return `${localReminders.length} set`
    }

    // Get time summary
    const getTimeSummary = (): string => {
        if (allDay) return "All day"
        return time || "Not set"
    }

    return (
        <Popover open={open} onOpenChange={handleOpenChange}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    className={cn(
                        "w-full justify-start text-left font-normal h-9 px-3",
                        !date && "text-muted-foreground"
                    )}
                    disabled={disabled}
                >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {date ? (
                        <span className="flex items-center gap-2 flex-1 min-w-0">
                            <span className="truncate">
                                {formatSmartDate(date, !allDay && !!time)}
                            </span>
                            {reminders.length > 0 && (
                                <Bell className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                            )}
                        </span>
                    ) : (
                        <span>{placeholder}</span>
                    )}
                    {date && (
                        <X
                            className="ml-auto h-4 w-4 opacity-50 hover:opacity-100 flex-shrink-0"
                            onClick={handleClear}
                        />
                    )}
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0 z-[120]" align="start">
                {/* Custom Month Header with Today Dot */}
                <div className="flex items-center justify-between px-3 py-2 border-b">
                    <span className="text-sm font-medium">
                        {format(month, "MMMM yyyy")}
                    </span>
                    <div className="flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => setMonth(subMonths(month, 1))}
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={handleGoToToday}
                            title="Go to today"
                        >
                            <Circle className="h-3 w-3" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => setMonth(addMonths(month, 1))}
                        >
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                {/* Calendar (compact) */}
                <Calendar
                    mode="single"
                    selected={date}
                    onSelect={handleDateSelect}
                    month={month}
                    onMonthChange={setMonth}
                    className="p-2"
                    classNames={{
                        months: "space-y-2",
                        month: "space-y-2",
                        caption: "hidden", // Hide default caption since we have custom header
                        nav: "hidden", // Hide default nav
                        table: "w-full border-collapse",
                        head_row: "flex",
                        head_cell: "text-muted-foreground rounded-md w-8 font-normal text-[0.7rem]",
                        row: "flex w-full mt-1",
                        cell: "h-8 w-8 text-center text-sm p-0 relative",
                        day: "h-8 w-8 p-0 font-normal hover:bg-accent hover:text-accent-foreground rounded-md",
                        day_selected: "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground",
                        day_today: "bg-accent text-accent-foreground",
                        day_outside: "text-muted-foreground opacity-50",
                        day_disabled: "text-muted-foreground opacity-50",
                    }}
                />

                {/* Time Section (Collapsible) - includes All Day toggle */}
                <div className="border-t">
                    <button
                        type="button"
                        className="w-full flex items-center justify-between px-3 py-1.5 hover:bg-muted/50 transition-colors"
                        onClick={() => setTimeExpanded(!timeExpanded)}
                    >
                        <div className="flex items-center gap-2">
                            <Clock className="h-3.5 w-3.5" />
                            <span className="text-sm">Time</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">{getTimeSummary()}</span>
                            {timeExpanded ? (
                                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                            ) : (
                                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                            )}
                        </div>
                    </button>
                    {timeExpanded && (
                        <div className="px-3 pb-2 space-y-2 animate-in slide-in-from-top-1">
                            {/* All Day Toggle */}
                            <div className="flex items-center justify-between py-1">
                                <Label htmlFor="all-day" className="text-xs text-muted-foreground">
                                    All day
                                </Label>
                                <Switch
                                    id="all-day"
                                    checked={allDay}
                                    onCheckedChange={handleAllDayToggle}
                                    className="scale-75"
                                />
                            </div>
                            {!allDay && (
                                <>
                                    <Input
                                        type="time"
                                        value={time}
                                        onChange={handleTimeChange}
                                        className="h-7 text-sm"
                                    />
                                    <div className="flex gap-1">
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="flex-1 text-xs h-6 px-2"
                                            onClick={() => handleTimePreset("09:00")}
                                        >
                                            9am
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="flex-1 text-xs h-6 px-2"
                                            onClick={() => handleTimePreset("12:00")}
                                        >
                                            12pm
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="flex-1 text-xs h-6 px-2"
                                            onClick={() => handleTimePreset("17:00")}
                                        >
                                            5pm
                                        </Button>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>

                {/* Reminder Section (Collapsible) */}
                <div className="border-t">
                    <button
                        type="button"
                        className="w-full flex items-center justify-between px-3 py-1.5 hover:bg-muted/50 transition-colors"
                        onClick={() => setReminderExpanded(!reminderExpanded)}
                    >
                        <div className="flex items-center gap-2">
                            <Bell className="h-3.5 w-3.5" />
                            <span className="text-sm">Reminder</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground truncate max-w-[100px]">
                                {getReminderSummary()}
                            </span>
                            {reminderExpanded ? (
                                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                            ) : (
                                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                            )}
                        </div>
                    </button>
                    {reminderExpanded && (
                        <div className="px-3 pb-2 space-y-1 animate-in slide-in-from-top-1">
                            {presets.map((preset) => (
                                <div
                                    key={preset.minutes}
                                    className="flex items-center space-x-2"
                                >
                                    <Checkbox
                                        id={`reminder-${preset.minutes}`}
                                        checked={localReminders.includes(preset.minutes)}
                                        onCheckedChange={(checked) =>
                                            handleReminderToggle(preset.minutes, checked === true)
                                        }
                                        className="h-3.5 w-3.5"
                                    />
                                    <Label
                                        htmlFor={`reminder-${preset.minutes}`}
                                        className="text-xs font-normal cursor-pointer flex-1"
                                    >
                                        {preset.label}
                                    </Label>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </PopoverContent>
        </Popover>
    )
}
