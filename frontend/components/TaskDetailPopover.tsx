"use client"

import { useState, useCallback, ReactNode, useEffect } from "react"
import useSWR, { mutate } from 'swr'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { PrioritySelect } from "@/components/PrioritySelect"
import { DatePicker } from "@/components/DatePicker"
import { MetadataRow } from "@/components/MetadataRow"
import { MarkdownEditor } from "@/components/MarkdownEditor"
import { SuggestionPanel } from "@/components/SuggestionPanel"
import { api } from "@/lib/api"
import { X, Trash2, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { Task, SuggestionsResponse, Suggestion } from "@/types/task"
import { ProjectSelector } from "@/components/metadata/ProjectSelector"
import { TagsInput } from "@/components/metadata/TagsInput"
import { RepeatPatternSelect } from "@/components/metadata/RepeatPatternSelect"
import { TimeEstimateInput } from "@/components/metadata/TimeEstimateInput"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const fetcher = (url: string) => fetch(url).then((r) => r.json())

interface TaskDetailPopoverProps {
  task: Task
  trigger: ReactNode
  onUpdate?: (task: Task) => void
  onDelete?: (taskId: number) => void
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

// Debounce hook
function useDebounce<T extends (...args: any[]) => void>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null)

  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      const newTimeoutId = setTimeout(() => {
        callback(...args)
      }, delay)
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
  const [analyzing, setAnalyzing] = useState(false)
  const [streamingSuggestions, setStreamingSuggestions] = useState<Suggestion[]>([])

  // Use controlled state if provided, otherwise use internal state
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen
  const setOpen = controlledOnOpenChange || setInternalOpen

  // Reset streaming state when dialog closes
  useEffect(() => {
    if (!open) {
      setStreamingSuggestions([])
      setAnalyzing(false)
    }
  }, [open])

  // Fetch suggestions
  const { data: suggestionsData } = useSWR<SuggestionsResponse>(
    open ? `${API_BASE}/api/tasks/${task.id}/suggestions?user_id=1` : null,
    fetcher,
    { refreshInterval: 0 } // Don't auto-refresh
  )

  const handleAnalyze = () => {
    setAnalyzing(true)
    setError(null)
    setStreamingSuggestions([])

    try {
      const source = new EventSource(`${API_BASE}/api/tasks/${task.id}/analyze/stream?user_id=1`)

      source.addEventListener("suggestion", (event: MessageEvent) => {
        try {
          const payload = JSON.parse(event.data)
          setStreamingSuggestions((prev) => [...prev, payload])
        } catch (e) {
          console.error("Failed to parse suggestion event", e)
        }
      })

      source.addEventListener("analysis", (event: MessageEvent) => {
        try {
          const payload = JSON.parse(event.data)
          setLocalTask((prev) => ({
            ...prev,
            urgency_score: payload?.urgency_score ?? prev.urgency_score,
            importance_score: payload?.importance_score ?? prev.importance_score,
            eisenhower_quadrant: payload?.eisenhower_quadrant ?? prev.eisenhower_quadrant,
            analysis_reasoning: payload?.analysis_reasoning ?? prev.analysis_reasoning,
          }))
        } catch (e) {
          console.error("Failed to parse analysis event", e)
        }
      })

      source.addEventListener("done", async () => {
        source.close()
        try {
          const refreshedTask = await api.get<Task>(`/api/tasks/${task.id}?user_id=1`)
          setLocalTask(refreshedTask)
          if (onUpdate) {
            onUpdate(refreshedTask)
          }
          mutate(`${API_BASE}/api/tasks/${task.id}/suggestions?user_id=1`)
        } catch (e) {
          console.error("Failed to refresh after streaming", e)
        } finally {
          setAnalyzing(false)
        }
      })

      source.onerror = (err) => {
        console.error("Streaming analyze failed:", err)
        setError("Failed to analyze task")
        source.close()
        setAnalyzing(false)
      }
    } catch (error) {
      console.error("Analysis failed:", error)
      setError("Failed to analyze task")
      setAnalyzing(false)
    }
  }

  const handleApproveSuggestion = async (types: string[]) => {
    try {
      await api.post(`/api/tasks/${task.id}/suggestions/approve?user_id=1`, {
        suggestion_types: types
      })
      setStreamingSuggestions([])

      // Refresh task data and suggestions
      const refreshedTask = await api.get<Task>(`/api/tasks/${task.id}?user_id=1`)
      setLocalTask(refreshedTask)
      if (onUpdate) {
        onUpdate(refreshedTask)
      }
      mutate(`${API_BASE}/api/tasks/${task.id}/suggestions?user_id=1`)
    } catch (error) {
      console.error('Approval failed:', error)
      setError('Failed to approve suggestion')
    }
  }

  const handleRejectSuggestion = async (types: string[]) => {
    try {
      await api.post(`/api/tasks/${task.id}/suggestions/reject?user_id=1`, {
        suggestion_types: types
      })
      setStreamingSuggestions([])

      mutate(`${API_BASE}/api/tasks/${task.id}/suggestions?user_id=1`)
    } catch (error) {
      console.error('Rejection failed:', error)
      setError('Failed to reject suggestion')
    }
  }

  const storedSuggestions = suggestionsData?.suggestions || []
  const displayedSuggestions = streamingSuggestions.length > 0 ? streamingSuggestions : storedSuggestions

  // Auto-save function
  const saveTask = async (updates: Partial<Task>) => {
    try {
      setSaving(true)
      setError(null)

      // Make API call to update task
      const response = await api.patch<Task>(`/api/tasks/${task.id}`, {
        ...updates,
        user_id: 1, // Hardcoded for single-user mode
      })

      // Update local state
      const updatedTask = { ...localTask, ...response }
      setLocalTask(updatedTask)

      // Notify parent
      if (onUpdate) {
        onUpdate(updatedTask)
      }
    } catch (err: any) {
      console.error("Failed to save task:", err)
      setError(err.message || "Failed to save changes")
    } finally {
      setSaving(false)
    }
  }

  // Debounced save for text fields
  const debouncedSave = useDebounce(saveTask, 800)

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
    if (!confirm("Are you sure you want to delete this task?")) return

    try {
      setSaving(true)
      await api.delete(`/api/tasks/${task.id}?user_id=1`)
      setOpen(false)
      if (onDelete) {
        onDelete(task.id)
      }
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

  const effectiveQuadrant =
    localTask.manual_quadrant_override ||
    localTask.effective_quadrant ||
    localTask.eisenhower_quadrant

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {trigger}
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <DialogHeader>
          <div className="flex items-start gap-3">
            <Checkbox
              checked={localTask.status === "completed"}
              onCheckedChange={handleToggleComplete}
              className="mt-1"
            />
            <div className="flex-1">
              <Input
                value={localTask.title}
                onChange={(e) => handleFieldChange("title", e.target.value)}
                className="text-lg font-semibold border-none px-0 focus-visible:ring-0"
                placeholder="Task title"
              />
            </div>
            <Button variant="ghost" size="icon" onClick={() => setOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {/* Error Alert */}
          {error && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-destructive mt-0.5" />
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {/* Metadata Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MetadataRow icon="📅" label="Due Date">
              <DatePicker
                value={localTask.due_date}
                onChange={(date) => handleFieldChange("due_date", date, true)}
                placeholder="No due date"
              />
            </MetadataRow>

            <MetadataRow icon="🏁" label="Start Date">
              <DatePicker
                value={localTask.start_date}
                onChange={(date) => handleFieldChange("start_date", date, true)}
                placeholder="No start date"
              />
            </MetadataRow>

            <MetadataRow icon="⭐" label="Priority">
              <PrioritySelect
                value={localTask.ticktick_priority || 0}
                onChange={(priority) => handleFieldChange("ticktick_priority", priority, true)}
              />
            </MetadataRow>

            <MetadataRow icon="🗂️" label="Project">
              <ProjectSelector
                value={localTask.project_id ?? null}
                onChange={(projectId, project) => {
                  handleFieldChange("project_id", projectId, true)
                  handleFieldChange("project_name", project?.name || null, true)
                  handleFieldChange("ticktick_project_id", project?.ticktick_project_id || null, true)
                }}
              />
            </MetadataRow>

            <MetadataRow icon="🔔" label="Reminder">
              <DatePicker
                value={localTask.reminder_time}
                onChange={(date) => handleFieldChange("reminder_time", date, true)}
                placeholder="No reminder"
              />
            </MetadataRow>

            <MetadataRow icon="🔁" label="Repeat">
              <RepeatPatternSelect
                value={localTask.repeat_flag}
                onChange={(pattern) => handleFieldChange("repeat_flag", pattern, true)}
              />
            </MetadataRow>

            <MetadataRow icon="⏱️" label="Time Estimate">
              <TimeEstimateInput
                value={localTask.time_estimate ?? null}
                onChange={(minutes) => handleFieldChange("time_estimate", minutes, true)}
              />
            </MetadataRow>

            <MetadataRow icon="☀️" label="All Day">
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={Boolean(localTask.all_day)}
                  onCheckedChange={(checked) => handleFieldChange("all_day", Boolean(checked), true)}
                />
                <span className="text-sm text-muted-foreground">All day</span>
              </div>
            </MetadataRow>
          </div>

          {/* Tags */}
          <div>
            <label className="text-sm text-muted-foreground mb-2 block">Tags</label>
            <TagsInput
              value={localTask.ticktick_tags || []}
              onChange={(tags) => handleFieldChange("ticktick_tags", tags, true)}
              placeholder="Add tags..."
            />
          </div>

          {/* Description with Markdown Support */}
          <MarkdownEditor
            value={localTask.description || ""}
            onChange={(desc) => handleFieldChange("description", desc)}
            placeholder="Add a description..."
          />

          {/* AI Analysis Section */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <span className="text-lg">🤖</span>
              AI Analysis
            </h3>

            {/* Show analyze button if no analysis yet and no suggestions */}
            {!analyzing && displayedSuggestions.length === 0 && !localTask.urgency_score && (
              <Button onClick={handleAnalyze} variant="outline" className="w-full">
                ⚡ Analyze with AI
              </Button>
            )}

            {/* Show analyzing state */}
            {analyzing && (
              <div className="text-center py-4">
                <p className="text-muted-foreground">🤔 Analyzing task...</p>
              </div>
            )}

            {/* Show suggestions if available */}
            {displayedSuggestions.length > 0 && (
              <SuggestionPanel
                suggestions={displayedSuggestions}
                onApprove={handleApproveSuggestion}
                onReject={handleRejectSuggestion}
              />
            )}

            {/* Show existing analysis */}
            {(localTask.urgency_score !== undefined || localTask.analysis_reasoning) && (
              <div className="space-y-3 bg-muted/50 p-4 rounded-lg mt-3">
                {effectiveQuadrant && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Quadrant:</span>
                    <Badge variant="outline">{effectiveQuadrant}</Badge>
                    {localTask.manual_quadrant_override && (
                      <Badge variant="secondary" className="text-xs">
                        Manual Override
                      </Badge>
                    )}
                  </div>
                )}

                {localTask.urgency_score !== undefined && localTask.importance_score !== undefined && (
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-muted-foreground">Urgency:</span>
                      <span className="ml-2 font-medium">{localTask.urgency_score}/10</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Importance:</span>
                      <span className="ml-2 font-medium">{localTask.importance_score}/10</span>
                    </div>
                  </div>
                )}

                {localTask.analysis_reasoning && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Reasoning:</p>
                    <p className="text-sm leading-relaxed">{localTask.analysis_reasoning}</p>
                  </div>
                )}

                {/* Re-analyze button */}
                {!analyzing && (
                  <Button
                    onClick={handleAnalyze}
                    variant="ghost"
                    size="sm"
                    className="w-full mt-2"
                  >
                    🔄 Re-analyze
                  </Button>
                )}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="flex justify-between items-center pt-4 border-t">
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={saving}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {saving && <span>Saving...</span>}
              {localTask.created_at && (
                <span>Created {new Date(localTask.created_at).toLocaleDateString()}</span>
              )}
              {localTask.ticktick_task_id && (
                <Badge variant="outline" className="text-xs">
                  TickTick
                </Badge>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
