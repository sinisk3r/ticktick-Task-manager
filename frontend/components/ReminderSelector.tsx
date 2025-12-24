"use client"

import * as React from "react"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { X, AlarmClock, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"
import { DatePickerWithOptionalTime } from "@/components/DatePickerWithOptionalTime"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"

interface ReminderSelectorProps {
    value: number[]  // Array of minutes-before integers (saved state)
    onChange: (reminders: number[]) => void  // Called when user confirms selection
    allDay: boolean  // Determines which preset options to show
    dueDate?: string | null  // Deadline datetime (for custom reminder calculation)
    onDraftChange?: (reminders: number[]) => void  // Optional: Called on every checkbox change for preview
}

// Preset options for date-only (allDay=true)
const DATE_ONLY_PRESETS = [
    { label: "On the day", minutes: 0 },
    { label: "1 day early", minutes: 1440 },
    { label: "2 days early", minutes: 2880 },
    { label: "3 days early", minutes: 4320 },
    { label: "1 week early", minutes: 10080 },
]

// Preset options for date+time (allDay=false)
const DATE_TIME_PRESETS = [
    { label: "On time", minutes: 0 },
    { label: "5 minutes early", minutes: 5 },
    { label: "15 minutes early", minutes: 15 },
    { label: "30 minutes early", minutes: 30 },
    { label: "1 hour early", minutes: 60 },
    { label: "2 hours early", minutes: 120 },
    { label: "1 day early", minutes: 1440 },
]

export function ReminderSelector({
    value,
    onChange,
    allDay,
    dueDate,
    onDraftChange
}: ReminderSelectorProps) {
    const [isOpen, setIsOpen] = React.useState(false)
    const [draftReminders, setDraftReminders] = React.useState<number[]>(value)
    const [showCustomPicker, setShowCustomPicker] = React.useState(false)
    const [customReminderDate, setCustomReminderDate] = React.useState<string | null>(null)

    // Initialize draft state from value prop when it changes
    React.useEffect(() => {
        setDraftReminders(value)
    }, [value])

    // Get preset options based on allDay flag
    const presets = allDay ? DATE_ONLY_PRESETS : DATE_TIME_PRESETS

    // Format minutes to human-readable string
    const formatMinutes = (minutes: number): string => {
        if (minutes === 0) return allDay ? "On the day" : "On time"
        if (minutes < 60) return `${minutes} min${minutes !== 1 ? "s" : ""} early`
        if (minutes < 1440) {
            const hours = Math.floor(minutes / 60)
            return `${hours} hour${hours !== 1 ? "s" : ""} early`
        }
        const days = Math.floor(minutes / 1440)
        return `${days} day${days !== 1 ? "s" : ""} early`
    }

    // Handle checkbox toggle
    const handlePresetToggle = (minutes: number, checked: boolean) => {
        let newDraft: number[]
        if (checked) {
            // Add to draft (avoid duplicates)
            newDraft = [...draftReminders, minutes].filter((v, i, arr) => arr.indexOf(v) === i)
        } else {
            // Remove from draft
            newDraft = draftReminders.filter(m => m !== minutes)
        }
        // Sort ascending
        newDraft.sort((a, b) => a - b)
        setDraftReminders(newDraft)
        
        // Call onDraftChange for preview (doesn't trigger save)
        if (onDraftChange) {
            onDraftChange(newDraft)
        }
    }

    // Handle custom reminder date selection
    const handleCustomDateSelect = (date: string | null) => {
        setCustomReminderDate(date)
        
        if (date && dueDate) {
            const reminderTime = new Date(date)
            const deadline = new Date(dueDate)
            const diffMs = deadline.getTime() - reminderTime.getTime()
            const diffMinutes = Math.round(diffMs / (1000 * 60))
            
            // Only add if reminder is before deadline and non-negative
            if (diffMinutes >= 0) {
                const newDraft = [...draftReminders, diffMinutes]
                    .filter((v, i, arr) => arr.indexOf(v) === i)
                    .sort((a, b) => a - b)
                setDraftReminders(newDraft)
                
                if (onDraftChange) {
                    onDraftChange(newDraft)
                }
                
                // Reset custom picker
                setCustomReminderDate(null)
                setShowCustomPicker(false)
            }
        } else if (date && !dueDate) {
            // If no due date, show error or disable custom option
            setCustomReminderDate(null)
            setShowCustomPicker(false)
        }
    }

    // Handle remove reminder badge
    const handleRemoveReminder = (minutes: number) => {
        const newDraft = draftReminders.filter(m => m !== minutes)
        setDraftReminders(newDraft)
        
        if (onDraftChange) {
            onDraftChange(newDraft)
        }
    }

    // Handle confirm (save)
    const handleConfirm = () => {
        onChange(draftReminders)
        setIsOpen(false)
    }

    // Handle cancel (revert to saved state)
    const handleCancel = () => {
        setDraftReminders(value)
        setIsOpen(false)
    }

    // Handle modal close
    const handleOpenChange = (open: boolean) => {
        if (!open) {
            // Revert to saved state on close without confirm
            setDraftReminders(value)
        }
        setIsOpen(open)
    }

    return (
        <div className="space-y-2">
            <Popover open={isOpen} onOpenChange={handleOpenChange}>
                <PopoverTrigger asChild>
                    <Button
                        variant="outline"
                        className="w-full justify-between"
                        onClick={() => setIsOpen(true)}
                    >
                        <div className="flex items-center gap-2">
                            <AlarmClock className="h-4 w-4" />
                            <span>
                                {draftReminders.length === 0
                                    ? "No reminders"
                                    : `${draftReminders.length} reminder${draftReminders.length !== 1 ? "s" : ""}`}
                            </span>
                        </div>
                        {isOpen ? (
                            <ChevronUp className="h-4 w-4 opacity-50" />
                        ) : (
                            <ChevronDown className="h-4 w-4 opacity-50" />
                        )}
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80 p-0" align="start">
                    <div className="p-4 space-y-4">
                        {/* Selected reminders display */}
                        {draftReminders.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                                {draftReminders.map((minutes) => {
                                    const preset = presets.find(p => p.minutes === minutes)
                                    return (
                                        <Badge
                                            key={minutes}
                                            variant="secondary"
                                            className="flex items-center gap-1"
                                        >
                                            {preset ? preset.label : formatMinutes(minutes)}
                                            <X
                                                className="h-3 w-3 cursor-pointer"
                                                onClick={() => handleRemoveReminder(minutes)}
                                            />
                                        </Badge>
                                    )
                                })}
                            </div>
                        )}

                        {/* Preset options */}
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Reminder Options</Label>
                            <div className="space-y-2">
                                {presets.map((preset) => (
                                    <div
                                        key={preset.minutes}
                                        className="flex items-center space-x-2"
                                    >
                                        <Checkbox
                                            id={`reminder-${preset.minutes}`}
                                            checked={draftReminders.includes(preset.minutes)}
                                            onCheckedChange={(checked) =>
                                                handlePresetToggle(preset.minutes, checked === true)
                                            }
                                        />
                                        <Label
                                            htmlFor={`reminder-${preset.minutes}`}
                                            className="text-sm font-normal cursor-pointer flex-1"
                                        >
                                            {preset.label}
                                        </Label>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Custom reminder option */}
                        <div className="space-y-2">
                            {showCustomPicker ? (
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Custom Reminder</Label>
                                    <DatePickerWithOptionalTime
                                        value={customReminderDate}
                                        onChange={handleCustomDateSelect}
                                        placeholder="Select reminder date & time"
                                    />
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => {
                                            setShowCustomPicker(false)
                                            setCustomReminderDate(null)
                                        }}
                                    >
                                        Cancel
                                    </Button>
                                </div>
                            ) : (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="w-full"
                                    onClick={() => setShowCustomPicker(true)}
                                    disabled={!dueDate}
                                    title={!dueDate ? "Set a due date first" : ""}
                                >
                                    Custom
                                </Button>
                            )}
                        </div>

                        {/* Action buttons */}
                        <div className="flex gap-2 pt-2 border-t">
                            <Button
                                variant="outline"
                                size="sm"
                                className="flex-1"
                                onClick={handleCancel}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="default"
                                size="sm"
                                className="flex-1"
                                onClick={handleConfirm}
                            >
                                OK
                            </Button>
                        </div>
                    </div>
                </PopoverContent>
            </Popover>
        </div>
    )
}

