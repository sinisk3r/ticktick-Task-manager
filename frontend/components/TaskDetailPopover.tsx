"use client"

import { ReactNode, useCallback, useMemo, useState, useRef, useEffect } from "react"
import { createPortal } from "react-dom"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { PrioritySelect } from "@/components/PrioritySelect"
import { DatePickerWithOptionalTime } from "@/components/DatePickerWithOptionalTime"
import { api, API_BASE } from "@/lib/api"
import { X, Trash2, AlertCircle, Sparkles, Calendar, Layout } from "lucide-react"
import { cn } from "@/lib/utils"
import { Task, EnhanceResponse } from "@/types/task"
import { ProjectSelector } from "@/components/metadata/ProjectSelector"
import { TagsInput } from "@/components/metadata/TagsInput"
import { RepeatPatternSelect } from "@/components/metadata/RepeatPatternSelect"
import { TimeEstimateInput } from "@/components/metadata/TimeEstimateInput"
import { CollapsibleDescription } from "@/components/CollapsibleDescription"
import { toast } from "sonner"
import useSWR from "swr"

interface TaskDetailPopoverProps {
  task: Task
  trigger: ReactNode
  onUpdate?: (task: Task) => void
  onDelete?: (taskId: number) => void
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

// Simplified suggestion types
interface SuggestionItem {
  id: string
  field: keyof Task | 'project' | 'tags'
  label: string
  value: any
  displayValue: string
}

const fetcher = (url: string) => fetch(url).then((r) => r.json())

// Debounce hook
function useDebounce<T extends (...args: any[]) => void>(callback: T, delay: number): (...args: Parameters<T>) => void {
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null)

  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutId) clearTimeout(timeoutId)
      const newTimeoutId = setTimeout(() => callback(...args), delay)
      setTimeoutId(newTimeoutId)
    },
    [callback, delay, timeoutId]
  )
}

export function TaskDetailPopover({
  task,
  trigger,
  onUpdate,
  onDelete,
  open: controlledOpen,
  onOpenChange: controlledOnOpenChange,
}: TaskDetailPopoverProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const [localTask, setLocalTask] = useState(task)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [mounted, setMounted] = useState(false)

  // AI State (simplified)
  const [enhancing, setEnhancing] = useState(false)
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([])
  const [rationale, setRationale] = useState<string | null>(null)

  // Fetch projects for matching
  const { data: projects } = useSWR<any[]>(`${API_BASE}/api/projects?user_id=1`, fetcher)

  // Sync state with open prop or internal state
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen
  const setOpen = controlledOnOpenChange || setInternalOpen

  useEffect(() => {
    setMounted(true)
  }, [])

  // Handle Escape key and body scroll lock
  useEffect(() => {
    if (!open) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
      }
    }

    // Lock body scroll
    document.body.style.overflow = 'hidden'

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [open, setOpen])

  // Calculate smart position based on cursor and viewport
  const calculatePosition = useCallback((e: MouseEvent) => {
    const popoverWidth = 680
    const popoverHeight = 600
    const padding = 20

    let x = e.clientX + 10 // Offset from cursor
    let y = e.clientY + 10

    // Check right edge
    if (x + popoverWidth > window.innerWidth - padding) {
      x = window.innerWidth - popoverWidth - padding
    }

    // Check bottom edge
    if (y + popoverHeight > window.innerHeight - padding) {
      y = window.innerHeight - popoverHeight - padding
    }

    // Ensure not off left/top
    x = Math.max(padding, x)
    y = Math.max(padding, y)

    setPosition({ x, y })
  }, [])

  const saveTask = async (updates: Partial<Task>) => {
    try {
      setSaving(true)
      setError(null)
      const response = await api.patch<Task>(`/api/tasks/${task.id}`, { ...updates, user_id: 1 })
      const updatedTask = { ...localTask, ...response }
      setLocalTask(updatedTask)
      onUpdate?.(updatedTask)
    } catch (err: any) {
      console.error("Failed to save task:", err)
      setError(err.message || "Failed to save changes")
    } finally {
      setSaving(false)
    }
  }

  const debouncedSave = useDebounce(saveTask, 700)

  const handleFieldChange = (field: keyof Task, value: any, immediate = false) => {
    const updates = { [field]: value }
    setLocalTask((prev) => ({ ...prev, ...updates }))
    if (immediate) {
      saveTask(updates)
    } else {
      debouncedSave(updates)
    }
  }

  const handleDelete = async () => {
    if (!confirm("Delete this task?")) return
    try {
      setSaving(true)
      await api.delete(`/api/tasks/${task.id}?user_id=1`)
      setOpen(false)
      onDelete?.(task.id)
    } catch (err: any) {
      console.error("Failed to delete task:", err)
      setError(err.message || "Failed to delete task")
    } finally {
      setSaving(false)
    }
  }

  const handleToggleComplete = () => {
    const newStatus = localTask.status === "completed" ? "active" : "completed"
    handleFieldChange("status", newStatus, true)
  }

  const handleEnhance = async () => {
    setEnhancing(true)
    setError(null)
    setSuggestions([])
    setRationale(null)

    try {
      const response = await api.post<EnhanceResponse>(
        `/api/tasks/${task.id}/enhance?user_id=1`,
        {
          enhance_description: true,
          enhance_dates: true,
          enhance_project: true,
          enhance_time: true,
        }
      )

      processSuggestions(response)
    } catch (err: any) {
      console.error("Enhance failed:", err)
      setError(err.message || "Failed to enhance task")
      toast.error(err.message || "Failed to enhance task")
    } finally {
      setEnhancing(false)
    }
  }

  const processSuggestions = (response: EnhanceResponse) => {
    setRationale(response.rationale || null)
    const newSuggestions: SuggestionItem[] = []

    if (response.suggested_description && response.suggested_description !== localTask.description) {
      newSuggestions.push({
        id: 'desc',
        field: 'description',
        label: 'Description',
        value: response.suggested_description,
        displayValue: response.suggested_description
      })
    }

    if (response.suggested_project) {
      // Attempt to match project
      let matchedProject = null
      if (projects) {
        const suggestName = (response.suggested_project.name || response.suggested_project.label || "").toLowerCase()
        matchedProject = projects.find(p => p.name.toLowerCase() === suggestName)
      }

      const projectValue = matchedProject ? {
        id: matchedProject.id,
        name: matchedProject.name,
        ticktick: matchedProject.ticktick_project_id
      } : response.suggested_project

      newSuggestions.push({
        id: 'proj',
        field: 'project',
        label: 'Project',
        value: projectValue,
        displayValue: matchedProject ? matchedProject.name : (response.suggested_project.name || "Unknown")
      })
    }

    if (response.suggested_reminder) {
      newSuggestions.push({
        id: 'rem',
        field: 'reminder_time',
        label: 'Reminder',
        value: response.suggested_reminder,
        displayValue: new Date(response.suggested_reminder).toLocaleString()
      })
    }

    if (response.suggested_time_estimate) {
      newSuggestions.push({
        id: 'time',
        field: 'time_estimate',
        label: 'Time Estimate',
        value: response.suggested_time_estimate,
        displayValue: `${response.suggested_time_estimate} mins`
      })
    }

    if (response.suggested_tags && response.suggested_tags.length > 0) {
      newSuggestions.push({
        id: 'tags',
        field: 'tags',
        label: 'Tags',
        value: response.suggested_tags,
        displayValue: response.suggested_tags.join(", ")
      })
    }

    setSuggestions(newSuggestions)
  }

  const applySuggestions = async () => {
    if (suggestions.length === 0) return

    const updates: Partial<Task> = {}

    suggestions.forEach(s => {
      if (s.field === 'description') updates.description = s.value
      else if (s.field === 'project') {
        updates.project_id = s.value.id
        updates.project_name = s.value.name
        updates.ticktick_project_id = s.value.ticktick
      }
      else if (s.field === 'reminder_time') updates.reminder_time = s.value
      else if (s.field === 'time_estimate') updates.time_estimate = s.value
      else if (s.field === 'tags') updates.ticktick_tags = s.value
    })

    if (Object.keys(updates).length > 0) {
      await saveTask(updates)
      setSuggestions([])
      setRationale(null)
      toast.success("Applied AI suggestions")
    }
  }

  const effectiveQuadrant = useMemo(
    () =>
      localTask.manual_quadrant_override ||
      localTask.effective_quadrant ||
      localTask.eisenhower_quadrant,
    [localTask]
  )

  // Clone trigger and add click handler
  const triggerWithHandler = typeof trigger === 'object' && trigger !== null && 'props' in trigger
    ? {
        ...trigger,
        props: {
          ...(trigger as any).props,
          onClick: (e: React.MouseEvent) => {
            calculatePosition(e.nativeEvent)
            setOpen(true)
            // Call original onClick if exists
            ;(trigger as any).props?.onClick?.(e)
          }
        }
      }
    : trigger

  return (
    <>
      {triggerWithHandler}

      {mounted && open && createPortal(
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 z-50 animate-in fade-in"
            onClick={() => setOpen(false)}
          />

          {/* Popover Content */}
          <div
            className="fixed z-[60] w-[680px] h-[600px] bg-background border rounded-lg shadow-lg overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200"
            style={{
              left: `${position.x}px`,
              top: `${position.y}px`,
            }}
            onClick={(e) => e.stopPropagation()}
          >

        {/* Header */}
        <div className="flex items-start justify-between p-4 px-6 border-b shrink-0 bg-background z-20">
          <div className="flex items-start gap-4 flex-1 mr-8">
            <Checkbox
              checked={localTask.status === "completed"}
              onCheckedChange={handleToggleComplete}
              className="mt-1.5 size-5"
            />
            <div className="flex-1 space-y-1">
              <Input
                value={localTask.title}
                onChange={(e) => handleFieldChange("title", e.target.value)}
                className="text-xl font-bold border-none px-0 h-auto focus-visible:ring-0 rounded-none shadow-none bg-transparent"
                placeholder="Task title"
              />
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {localTask.project_name && (
                  <div className="flex items-center gap-1 bg-muted/50 px-1.5 py-0.5 rounded">
                    <div className="size-2 rounded-full bg-primary" />
                    {localTask.project_name}
                  </div>
                )}
                {localTask.created_at && <span>Created {new Date(localTask.created_at).toLocaleDateString()}</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="text-muted-foreground hover:text-destructive h-8 w-8"
              onClick={handleDelete}
            >
              <Trash2 className="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setOpen(false)}
            >
              <X className="size-5" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-hidden flex">
          {/* LEFT COLUMN: Properties */}
          <div className="w-[240px] shrink-0 border-r overflow-y-auto bg-muted/5 p-4 space-y-5">

            <div className="space-y-3">
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Layout className="size-3" /> Properties
              </h3>
              <div className="grid gap-3 pl-1">
                <div className="grid gap-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Priority</label>
                  <PrioritySelect
                    value={localTask.ticktick_priority || 0}
                    onChange={(priority) => handleFieldChange("ticktick_priority", priority, true)}
                  />
                </div>
                <div className="grid gap-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Project</label>
                  <ProjectSelector
                    value={localTask.project_id ?? null}
                    onChange={(projectId, project) => {
                      handleFieldChange("project_id", projectId, true)
                      handleFieldChange("project_name", project?.name || null, true)
                      handleFieldChange("ticktick_project_id", project?.ticktick_project_id || null, true)
                    }}
                  />
                </div>
                <div className="grid gap-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Tags</label>
                  <TagsInput
                    value={localTask.ticktick_tags || []}
                    onChange={(tags) => handleFieldChange("ticktick_tags", tags, true)}
                    placeholder="Add tags..."
                  />
                </div>
                <div className="grid gap-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Time Estimate</label>
                  <TimeEstimateInput
                    value={localTask.time_estimate ?? null}
                    onChange={(minutes) => handleFieldChange("time_estimate", minutes, true)}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3 pt-2 border-t border-dashed">
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Calendar className="size-3" /> Schedule
              </h3>
              <div className="grid gap-3 pl-1">
                {/* Stack dates vertically to prevent overlap */}
                <div className="space-y-3">
                  <div className="grid gap-1.5">
                    <label className="text-xs font-medium text-muted-foreground">Due By</label>
                    <DatePickerWithOptionalTime
                      value={localTask.due_date}
                      onChange={(date) => handleFieldChange("due_date", date, true)}
                      placeholder="Set due date..."
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-medium text-muted-foreground">Start Date</label>
                    <DatePickerWithOptionalTime
                      value={localTask.start_date}
                      onChange={(date) => handleFieldChange("start_date", date, true)}
                      placeholder="Set start date..."
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-medium text-muted-foreground">Reminder</label>
                    <DatePickerWithOptionalTime
                      value={localTask.reminder_time}
                      onChange={(date) => handleFieldChange("reminder_time", date, true)}
                      placeholder="Set reminder..."
                    />
                  </div>
                </div>
              </div>
            </div>

            {effectiveQuadrant && (
              <div className="pt-2 border-t border-dashed">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground text-xs font-medium">Quadrant:</span>
                  <Badge variant="outline" className="font-mono">{effectiveQuadrant}</Badge>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Description Editor + AI Suggestions */}
          <div className="flex-1 flex flex-col h-full bg-background relative min-w-0">
            {/* Collapsible Description */}
            <div className="flex-1 overflow-hidden">
              <CollapsibleDescription
                value={localTask.description || ""}
                onChange={(val) => handleFieldChange("description", val)}
              />
            </div>

            {/* AI Suggestions Section */}
            <div className="border-t p-4 space-y-3">
              {suggestions.length === 0 && !enhancing && (
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full gap-2"
                  onClick={handleEnhance}
                >
                  <Sparkles className="size-4" />
                  Get AI suggestions
                </Button>
              )}

              {enhancing && (
                <div className="space-y-2 py-4">
                  <div className="h-3 bg-muted/20 animate-pulse rounded w-3/4" />
                  <div className="h-3 bg-muted/20 animate-pulse rounded w-1/2" />
                  <p className="text-xs text-center text-muted-foreground animate-pulse mt-2">
                    Analyzing...
                  </p>
                </div>
              )}

              {suggestions.length > 0 && (
                <div className="space-y-3 animate-in fade-in slide-in-from-bottom-2">
                  {rationale && (
                    <div className="bg-muted p-2 rounded text-xs italic text-muted-foreground">
                      {rationale}
                    </div>
                  )}

                  <div className="space-y-2">
                    {suggestions.map(s => (
                      <div
                        key={s.id}
                        className="bg-muted/50 p-2 rounded text-sm border"
                      >
                        <span className="font-medium text-xs text-muted-foreground">
                          {s.label}:
                        </span>{" "}
                        <span className="text-sm">{s.displayValue}</span>
                      </div>
                    ))}
                  </div>

                  <Button
                    size="sm"
                    onClick={applySuggestions}
                    className="w-full gap-2"
                  >
                    <Sparkles className="size-4" />
                    Apply all suggestions
                  </Button>
                </div>
              )}
            </div>
          </div>

        </div>

            {error && (
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-destructive text-destructive-foreground px-4 py-2 rounded-full text-sm shadow-lg flex items-center gap-2 animate-in fade-in slide-in-from-bottom-4 z-[70]">
                <AlertCircle className="size-4" />
                {error}
                <Button variant="ghost" size="icon" className="h-4 w-4 rounded-full hover:bg-white/20" onClick={() => setError(null)}>
                  <X className="size-3" />
                </Button>
              </div>
            )}
          </div>
        </>,
        document.body
      )}
    </>
  )
}
