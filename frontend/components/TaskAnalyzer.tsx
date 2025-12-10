"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { RefreshCw, CheckCircle2 } from "lucide-react"

interface AnalysisResult {
  urgency_score: number
  importance_score: number
  eisenhower_quadrant: string
  reasoning: string
}

interface SyncResult {
  synced_count: number
  analyzed_count: number
  failed_count: number
  message: string
}

export function TaskAnalyzer() {
  const [taskDescription, setTaskDescription] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Sync state
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)

  const analyzeTask = async () => {
    if (!taskDescription.trim()) {
      setError("Please enter a task description")
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch("http://127.0.0.1:8000/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          description: taskDescription,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze task. Make sure the backend is running.")
    } finally {
      setLoading(false)
    }
  }

  const syncTicktickTasks = async () => {
    setSyncing(true)
    setSyncError(null)
    setSyncResult(null)

    try {
      const response = await fetch("http://127.0.0.1:8000/api/tasks/sync?user_id=1", {
        method: "POST",
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setSyncResult(data)
    } catch (err) {
      setSyncError(
        err instanceof Error
          ? err.message
          : "Failed to sync TickTick tasks. Make sure you're connected."
      )
    } finally {
      setSyncing(false)
    }
  }

  const getQuadrantColor = (quadrant: string) => {
    switch (quadrant) {
      case "Q1":
        return "bg-red-900/50 border-red-700"
      case "Q2":
        return "bg-green-900/50 border-green-700"
      case "Q3":
        return "bg-yellow-900/50 border-yellow-700"
      case "Q4":
        return "bg-blue-900/50 border-blue-700"
      default:
        return "bg-gray-800 border-gray-700"
    }
  }

  const getQuadrantLabel = (quadrant: string) => {
    switch (quadrant) {
      case "Q1":
        return "Urgent & Important"
      case "Q2":
        return "Not Urgent, Important"
      case "Q3":
        return "Urgent, Not Important"
      case "Q4":
        return "Neither Urgent nor Important"
      default:
        return quadrant
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Sync TickTick Tasks</CardTitle>
          <CardDescription>
            Sync and analyze your tasks from TickTick
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            onClick={syncTicktickTasks}
            disabled={syncing}
            className="w-full flex items-center justify-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Syncing Tasks..." : "Sync TickTick Tasks"}
          </Button>

          {syncResult && (
            <Alert className="border-green-700 bg-green-900/50">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <AlertDescription className="text-sm">
                <p className="font-medium">{syncResult.message}</p>
                <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">Synced:</span>{" "}
                    <span className="font-bold">{syncResult.synced_count}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Analyzed:</span>{" "}
                    <span className="font-bold">{syncResult.analyzed_count}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Failed:</span>{" "}
                    <span className="font-bold">{syncResult.failed_count}</span>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {syncError && (
            <Alert variant="destructive">
              <AlertDescription className="text-sm">{syncError}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Analyze Task</CardTitle>
          <CardDescription>
            Enter a task description to analyze its urgency and importance
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="task-input" className="text-sm font-medium text-gray-300">
              Task Description
            </label>
            <Textarea
              id="task-input"
              placeholder="e.g., Review and merge the critical security patch PR by end of day"
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              rows={4}
              className="resize-none"
            />
          </div>

          <Button
            onClick={analyzeTask}
            disabled={loading || !taskDescription.trim()}
            className="w-full"
          >
            {loading ? "Analyzing..." : "Analyze Task"}
          </Button>

          {error && (
            <div className="rounded-md bg-red-900/50 border border-red-700 p-4">
              <p className="text-sm text-red-200">{error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {result && (
        <Card className={getQuadrantColor(result.eisenhower_quadrant)}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Analysis Results</span>
              <span className="text-sm font-normal px-3 py-1 rounded-full bg-gray-900/50">
                {result.eisenhower_quadrant}: {getQuadrantLabel(result.eisenhower_quadrant)}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-300">Urgency Score</div>
                <div className="text-3xl font-bold">{result.urgency_score}/10</div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${result.urgency_score * 10}%` }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-300">Importance Score</div>
                <div className="text-3xl font-bold">{result.importance_score}/10</div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full transition-all"
                    style={{ width: `${result.importance_score * 10}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-300">Reasoning</div>
              <div className="text-sm text-gray-200 bg-gray-900/50 p-4 rounded-md">
                {result.reasoning}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
