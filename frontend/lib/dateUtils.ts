import { format, isToday, isTomorrow, isYesterday, isSameDay } from "date-fns"

/**
 * Check if a date string has a time component (not midnight)
 */
export function hasTimeComponent(dateStr: string | null | undefined): boolean {
    if (!dateStr) return false
    const d = new Date(dateStr)
    return d.getHours() !== 0 || d.getMinutes() !== 0
}

/**
 * Format a date as a smart label like "Today", "Tomorrow", "Dec 25"
 * Optionally includes time suffix when time is set
 */
export function formatSmartDate(
    date: string | Date | null,
    includeTime: boolean = true
): string {
    if (!date) return ""

    const d = date instanceof Date ? date : new Date(date)
    if (isNaN(d.getTime())) return ""

    let dateStr: string
    if (isToday(d)) {
        dateStr = "Today"
    } else if (isTomorrow(d)) {
        dateStr = "Tomorrow"
    } else if (isYesterday(d)) {
        dateStr = "Yesterday"
    } else {
        // Format as "Dec 25" for current year, "Dec 25, 2024" for other years
        const currentYear = new Date().getFullYear()
        if (d.getFullYear() === currentYear) {
            dateStr = format(d, "MMM d")
        } else {
            dateStr = format(d, "MMM d, yyyy")
        }
    }

    const dateIso = date instanceof Date ? date.toISOString() : date
    if (includeTime && hasTimeComponent(dateIso)) {
        return `${dateStr}, ${format(d, "HH:mm")}`
    }
    return dateStr
}

/**
 * Format reminder minutes to human-readable string
 * @param minutes - Minutes before deadline
 * @param allDay - Whether the task is all-day (affects "On time" vs "On the day" label)
 */
export function formatReminderMinutes(minutes: number, allDay: boolean = false): string {
    if (minutes === 0) return allDay ? "On the day" : "On time"
    if (minutes < 60) return `${minutes} min${minutes !== 1 ? "s" : ""} early`
    if (minutes < 1440) {
        const hours = Math.floor(minutes / 60)
        return `${hours} hour${hours !== 1 ? "s" : ""} early`
    }
    const days = Math.floor(minutes / 1440)
    return `${days} day${days !== 1 ? "s" : ""} early`
}

/**
 * Format reminder minutes to short form (e.g., "30m", "2h", "1d")
 */
export function formatReminderMinutesShort(minutes: number): string {
    if (minutes === 0) return "now"
    if (minutes < 60) return `${minutes}m`
    if (minutes < 1440) return `${Math.floor(minutes / 60)}h`
    return `${Math.floor(minutes / 1440)}d`
}

/**
 * Get reminder summary string for display
 */
export function formatRemindersSummary(
    reminders: number[],
    allDay: boolean = false
): string {
    if (!reminders || reminders.length === 0) return "No reminders"
    if (reminders.length === 1) {
        return formatReminderMinutes(reminders[0], allDay)
    }
    return `${reminders.length} reminders`
}

/**
 * Check if two dates are the same day
 */
export { isSameDay, isToday, isTomorrow, isYesterday }
