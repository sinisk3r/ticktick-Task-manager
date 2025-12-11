"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { PrioritySelect } from "@/components/PrioritySelect"
import { DatePicker } from "@/components/DatePicker"
import { MetadataRow } from "@/components/MetadataRow"
import { Plus, Sparkles, AlertCircle, Loader2 } from "lucide-react"
import { mutate } from "swr"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface QuickAddTaskModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface LLMSuggestion {
  urgency_score?: number
  importance_score?: number
  eisenhower_quadrant?: string
  ticktick_priority?: number
  analysis_reasoning?: string
}

export function QuickAddTaskModal({ open, onOpenChange }: QuickAddTaskModalProps) {
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [dueDate, setDueDate] = useState<string | null>(null)
  const [priority, setPriority] = useState(0)
  const [analyzing, setAnalyzing] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [llmSuggestion, setLlmSuggestion] = useState<LLMSuggestion | null>(null)

  const handleAnalyze = async () => {
    if (!description.trim()) {
      setError("Please add a description to get AI suggestions")
      return
    }

    setAnalyzing(true)
    setError(null)

    try {
      // Create a temporary task object for analysis
      const tempTask = {
        title: title || "Untitled Task",
        description: description,
        due_date: dueDate,
        user_id: 1
      }

      // Call the LLM analysis endpoint directly
      const response = await fetch(`${API_BASE}/api/tasks/analyze-quick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tempTask)
      })

      if (!response.ok) {
        throw new Error('Analysis failed')
      }

      const analysis = await response.json()

      // Store suggestions
      setLlmSuggestion({
        urgency_score: analysis.urgency_score,
        importance_score: analysis.importance_score,
        eisenhower_quadrant: analysis.eisenhower_quadrant,
        ticktick_priority: analysis.suggested_priority || 0,
        analysis_reasoning: analysis.analysis_reasoning
      })

      // Auto-apply suggested priority
      if (analysis.suggested_priority !== undefined) {
        setPriority(analysis.suggested_priority)
      }
    } catch (err: any) {
      console.error('Analysis error:', err)
      setError(err.message || 'Failed to analyze task')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleCreate = async () => {
    if (!title.trim()) {
      setError("Please enter a task title")
      return
    }

    setCreating(true)
    setError(null)

    try {
      const taskData = {
        title: title.trim(),
        description: description.trim() || null,
        due_date: dueDate,
        user_id: 1
      }

      const response = await fetch(`${API_BASE}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskData)
      })

      if (!response.ok) {
        throw new Error('Failed to create task')
      }

      const createdTask = await response.json()

      // Refresh task lists
      mutate(`${API_BASE}/api/tasks?user_id=1&status=active&limit=200`)
      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`)

      // Reset form
      setTitle("")
      setDescription("")
      setDueDate(null)
      setPriority(0)
      setLlmSuggestion(null)

      // Close modal
      onOpenChange(false)
    } catch (err: any) {
      console.error('Create error:', err)
      setError(err.message || 'Failed to create task')
    } finally {
      setCreating(false)
    }
  }

  const handleClose = () => {
    // Reset form on close
    setTitle("")
    setDescription("")
    setDueDate(null)
    setPriority(0)
    setLlmSuggestion(null)
    setError(null)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            Quick Add Task
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Title */}
          <div>
            <label className="text-sm font-medium mb-2 block">Task Title *</label>
            <Input
              placeholder="What needs to be done?"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium mb-2 block">Description</label>
            <Textarea
              placeholder="Add details about this task..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="resize-none"
            />
          </div>

          {/* AI Analysis Button */}
          <Button
            onClick={handleAnalyze}
            disabled={analyzing || !description.trim()}
            variant="outline"
            className="w-full"
          >
            {analyzing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                Get AI Suggestions
              </>
            )}
          </Button>

          {/* LLM Suggestions Display */}
          {llmSuggestion && (
            <div className="p-4 bg-accent/10 border border-accent/20 rounded-lg space-y-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-accent" />
                <h3 className="text-sm font-semibold">AI Suggestions</h3>
              </div>

              {llmSuggestion.eisenhower_quadrant && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Quadrant:</span>
                  <Badge variant="outline">{llmSuggestion.eisenhower_quadrant}</Badge>
                </div>
              )}

              {(llmSuggestion.urgency_score !== undefined || llmSuggestion.importance_score !== undefined) && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {llmSuggestion.urgency_score !== undefined && (
                    <div>
                      <span className="text-muted-foreground">Urgency:</span>
                      <span className="ml-2 font-medium">{llmSuggestion.urgency_score}/10</span>
                    </div>
                  )}
                  {llmSuggestion.importance_score !== undefined && (
                    <div>
                      <span className="text-muted-foreground">Importance:</span>
                      <span className="ml-2 font-medium">{llmSuggestion.importance_score}/10</span>
                    </div>
                  )}
                </div>
              )}

              {llmSuggestion.ticktick_priority !== undefined && llmSuggestion.ticktick_priority > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Suggested Priority:</span>
                  <Badge variant="secondary">
                    {llmSuggestion.ticktick_priority === 5 ? 'High' :
                     llmSuggestion.ticktick_priority === 3 ? 'Medium' : 'Low'}
                  </Badge>
                  <span className="text-xs text-muted-foreground">(Applied automatically)</span>
                </div>
              )}

              {llmSuggestion.analysis_reasoning && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Reasoning:</p>
                  <p className="text-sm leading-relaxed italic">{llmSuggestion.analysis_reasoning}</p>
                </div>
              )}
            </div>
          )}

          {/* Metadata Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MetadataRow icon="📅" label="Due Date">
              <DatePicker
                value={dueDate}
                onChange={(date) => setDueDate(date)}
                placeholder="No due date"
              />
            </MetadataRow>

            <MetadataRow icon="⭐" label="Priority">
              <PrioritySelect
                value={priority}
                onChange={setPriority}
              />
            </MetadataRow>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              variant="ghost"
              onClick={handleClose}
              disabled={creating}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={creating || !title.trim()}
            >
              {creating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Task
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
