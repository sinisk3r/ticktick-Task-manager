"use client"

import { forwardRef, useMemo, memo } from "react"
import { Badge } from "@/components/ui/badge"
import { Task } from "@/types/task"
import { format, isToday, isThisWeek, isPast } from "date-fns"
import { cn } from "@/lib/utils"
import { getQuadrant } from "@/lib/taskUtils"
import { motion } from "framer-motion"

interface ListTaskCardProps extends React.HTMLAttributes<HTMLDivElement> {
    task: Task
    onToggleStatus?: (task: Task) => void
}

// Checkbox SVG
const CheckIcon = memo(() => (
    <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
))
CheckIcon.displayName = "CheckIcon"

const PRIORITY_LABELS: { [key: number]: string } = {
    0: "None",
    1: "Low",
    3: "Medium",
    5: "High",
}

export const ListTaskCard = memo(forwardRef<HTMLDivElement, ListTaskCardProps>(
    ({ task, onToggleStatus, className, onClick, ...props }, ref) => {

        const quadrant = useMemo(() => getQuadrant(task), [task])

        const priorityLabel = useMemo(
            () => PRIORITY_LABELS[task.ticktick_priority || 0] || "None",
            [task.ticktick_priority]
        )

        const { isOverdue: taskIsOverdue, formattedDate } = useMemo(() => {
            if (!task.due_date) {
                return { isOverdue: false, formattedDate: null }
            }
            const date = new Date(task.due_date)
            const overdue = isPast(date) && !isToday(date)
            let formatted: string | null = null
            if (isToday(date)) {
                formatted = "Today"
            } else if (isThisWeek(date)) {
                formatted = format(date, "EEE")
            } else {
                formatted = format(date, "MMM d")
            }
            return { isOverdue: overdue, formattedDate: formatted }
        }, [task.due_date])

        const isCompleted = task.status === "completed"
        const checkboxClassName = isCompleted
            ? "size-5 shrink-0 rounded-[6px] border border-primary shadow-xs transition-all flex items-center justify-center hover:bg-primary/5 dark:bg-input/30"
            : "size-5 shrink-0 rounded-[6px] border border-primary shadow-xs transition-all flex items-center justify-center hover:bg-primary/5 dark:bg-input/30"

        return (
            <div
                ref={ref}
                className={cn(
                    "group w-full flex items-start gap-4 p-4 bg-card rounded-xl border border-border hover:border-primary/50 cursor-pointer transition-all hover:shadow-sm",
                    isCompleted && "border-primary/50 opacity-80",
                    className
                )}
                onClick={onClick}
                {...props}
            >
                {/* Checkbox (Interactive) */}
                <div
                    className={cn("mt-1 cursor-pointer", checkboxClassName)}
                    onClick={(e) => {
                        e.stopPropagation()
                        onToggleStatus?.(task)
                    }}
                >
                    {isCompleted && <CheckIcon />}
                </div>

                <div className="flex-1 min-w-0 space-y-2">
                    {/* Title */}
                    <div className="relative inline-block">
                        <h3 className={cn(
                            "text-base font-semibold leading-none mb-1 transition-colors duration-300",
                            isCompleted ? "text-muted-foreground" : "text-foreground"
                        )}>
                            {task.title}
                        </h3>
                        {/* Animated Strikethrough Line */}
                        <motion.div
                            initial={false}
                            animate={{ width: isCompleted ? "100%" : "0%" }}
                            transition={{ duration: 0.4, ease: "easeInOut" }}
                            className="absolute top-[8px] left-0 h-[2px] bg-primary/60 pointer-events-none"
                            style={{ transformOrigin: "left center" }}
                        />

                        {task.description && (
                            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                                {task.description}
                            </p>
                        )}
                    </div>

                    {/* Badges Row */}
                    <div className="flex flex-wrap gap-2">
                        {task.project_name && (
                            <Badge variant="outline" className="text-xs font-normal">
                                {task.project_name}
                            </Badge>
                        )}
                        {(task.ticktick_priority || 0) > 0 && (
                            <Badge variant="secondary" className="text-xs font-normal">
                                {priorityLabel}
                            </Badge>
                        )}
                        {formattedDate && (
                            <Badge variant={taskIsOverdue ? "destructive" : "secondary"} className="text-xs font-normal">
                                {formattedDate}
                            </Badge>
                        )}
                        {quadrant && (
                            <Badge variant="default" className="text-xs font-normal bg-primary/10 text-primary border-primary/20 hover:bg-primary/20">
                                {quadrant}
                            </Badge>
                        )}
                        {task.ticktick_tags?.map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs font-normal opacity-80">
                                #{tag}
                            </Badge>
                        ))}
                    </div>
                </div>
            </div>
        )
    }))

ListTaskCard.displayName = "ListTaskCard"
