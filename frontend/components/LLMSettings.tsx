"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CheckCircle2, XCircle, Loader2, Info, Link as LinkIcon, Unlink } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Textarea } from "@/components/ui/textarea"
import { API_BASE } from "@/lib/api"

export function LLMSettings() {
  const [selectedModel, setSelectedModel] = useState("qwen3:4b")
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "disconnected" | "testing">("disconnected")
  const [statusMessage, setStatusMessage] = useState<string>("")
  const [saveMessage, setSaveMessage] = useState<string>("")
  const [backendUrl] = useState(API_BASE)

  // TickTick state
  const [ticktickConnected, setTicktickConnected] = useState(false)
  const [ticktickUserId, setTicktickUserId] = useState<string | null>(null)
  const [ticktickStatus, setTicktickStatus] = useState<"checking" | "ready">("ready")

  // Profile context state
  const [peopleText, setPeopleText] = useState("")
  const [petsText, setPetsText] = useState("")
  const [activitiesText, setActivitiesText] = useState("")
  const [notesText, setNotesText] = useState("")
  const [profileMessage, setProfileMessage] = useState("")
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileSaving, setProfileSaving] = useState(false)

  const parseList = (text: string) =>
    text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
  const listToText = (items?: string[]) => (items && items.length ? items.join("\n") : "")

  // Load settings and fetch available models on mount
  useEffect(() => {
    const savedModel = localStorage.getItem("llm_model")
    if (savedModel) setSelectedModel(savedModel)

    // Fetch available models and test connection
    fetchModels()

    // Check TickTick connection status
    checkTicktickStatus()
    // Load personal context
    loadProfile()
  }, [])

  const checkTicktickStatus = async () => {
    setTicktickStatus("checking")
    try {
      const response = await fetch(`${backendUrl}/auth/ticktick/status`)
      if (response.ok) {
        const data = await response.json()
        setTicktickConnected(data.connected)
        setTicktickUserId(data.ticktick_user_id)
      }
    } catch (err) {
      console.error("Failed to check TickTick status:", err)
    } finally {
      setTicktickStatus("ready")
    }
  }

  const connectTicktick = () => {
    // Redirect to backend OAuth URL
    window.location.href = `${backendUrl}/auth/ticktick/authorize`
  }

  const disconnectTicktick = async () => {
    try {
      const response = await fetch(`${backendUrl}/auth/ticktick/disconnect`, {
        method: "POST",
      })

      if (response.ok) {
        setTicktickConnected(false)
        setTicktickUserId(null)
        setSaveMessage("TickTick disconnected successfully")
        setTimeout(() => setSaveMessage(""), 3000)
      }
    } catch (err) {
      console.error("Failed to disconnect TickTick:", err)
    }
  }

  const loadProfile = async () => {
    setProfileLoading(true)
    try {
      const response = await fetch(`${backendUrl}/api/profile?user_id=1`)
      if (response.ok) {
        const data = await response.json()
        setPeopleText(listToText(data.people))
        setPetsText(listToText(data.pets))
        setActivitiesText(listToText(data.activities))
        setNotesText(data.notes || "")
      }
    } catch (err) {
      console.error("Failed to load profile:", err)
      setProfileMessage("Unable to load personal context")
    } finally {
      setProfileLoading(false)
    }
  }

  const saveProfile = async () => {
    setProfileSaving(true)
    setProfileMessage("")
    try {
      const payload = {
        people: parseList(peopleText),
        pets: parseList(petsText),
        activities: parseList(activitiesText),
        notes: notesText.trim() || null,
      }
      const response = await fetch(`${backendUrl}/api/profile?user_id=1`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (response.ok) {
        setProfileMessage("Personal context saved")
      } else {
        setProfileMessage("Failed to save personal context")
      }
    } catch (err) {
      console.error("Failed to save profile:", err)
      setProfileMessage("Failed to save personal context")
    } finally {
      setProfileSaving(false)
      setTimeout(() => setProfileMessage(""), 3000)
    }
  }

  const fetchModels = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/llm/models`)
      if (response.ok) {
        const data = await response.json()
        setAvailableModels(data.models || [])
        // Auto-test connection after fetching models
        testConnection()
      }
    } catch (err) {
      console.error("Failed to fetch models:", err)
      setAvailableModels(["qwen3:4b", "qwen3:8b"]) // Fallback defaults
    }
  }

  const testConnection = async () => {
    setConnectionStatus("testing")
    setStatusMessage("Testing backend connection...")

    try {
      const response = await fetch(`${backendUrl}/api/llm/health`, {
        method: "GET",
      })

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`)
      }

      const data = await response.json()

      if (data.status === "ok") {
        setConnectionStatus("connected")
        setStatusMessage(`Connected to backend - Ollama model: ${data.model}`)
      } else {
        setConnectionStatus("disconnected")
        setStatusMessage(data.message || "Backend connection failed")
      }
    } catch (err) {
      setConnectionStatus("disconnected")
      setStatusMessage(
        err instanceof Error
          ? `Error: ${err.message}`
          : "Failed to connect to backend. Make sure it's running on port 8000."
      )
    }
  }

  const saveSettings = () => {
    localStorage.setItem("llm_model", selectedModel)
    setSaveMessage(`Settings saved! Model: ${selectedModel}`)

    // Clear save message after 3 seconds
    setTimeout(() => setSaveMessage(""), 3000)
  }

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case "connected":
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case "disconnected":
        return <XCircle className="h-5 w-5 text-red-500" />
      case "testing":
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
    }
  }

  const getStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "border-green-200 bg-green-100 dark:border-green-700 dark:bg-green-900/50"
      case "disconnected":
        return "border-red-200 bg-red-100 dark:border-red-700 dark:bg-red-900/50"
      case "testing":
        return "border-blue-200 bg-blue-100 dark:border-blue-700 dark:bg-blue-900/50"
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Backend & LLM Settings</CardTitle>
          <CardDescription>
            Configure your Ollama model for task analysis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Backend URL</label>
              <div className="p-3 bg-muted/50 rounded-md border border-border">
                <code className="text-sm text-foreground">{backendUrl}</code>
              </div>
              <p className="text-xs text-muted-foreground">
                The backend server handles all LLM communication
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Ollama Model</label>
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent>
                  {availableModels.map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                qwen3:4b is faster, qwen3:8b is more accurate
              </p>
            </div>

            <div className="flex gap-3">
              <Button onClick={testConnection} variant="outline" className="flex-1">
                {connectionStatus === "testing" ? "Testing..." : "Test Connection"}
              </Button>
              <Button onClick={saveSettings} className="flex-1">
                Save Settings
              </Button>
            </div>

            {saveMessage && (
              <Alert className="border-green-200 bg-green-100 dark:border-green-700 dark:bg-green-900/50">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <AlertDescription className="text-green-200">
                  {saveMessage}
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className={getStatusColor()}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {getStatusIcon()}
            Connection Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Status:</span>
              <span className="text-sm capitalize">{connectionStatus}</span>
            </div>
            {statusMessage && (
              <div className="text-sm text-muted-foreground mt-2">
                {statusMessage}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>TickTick Integration</CardTitle>
          <CardDescription>
            Connect your TickTick account to sync and analyze your tasks
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-md border border-border">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-background rounded-full">
                {ticktickStatus === "checking" ? (
                  <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                ) : ticktickConnected ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium">
                  {ticktickConnected ? "Connected to TickTick" : "Not Connected"}
                </p>
                {ticktickUserId && (
                  <p className="text-xs text-muted-foreground">
                    User ID: {ticktickUserId}
                  </p>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              {ticktickConnected ? (
                <Button
                  onClick={disconnectTicktick}
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-2"
                >
                  <Unlink className="h-4 w-4" />
                  Disconnect
                </Button>
              ) : (
                <Button
                  onClick={connectTicktick}
                  size="sm"
                  className="flex items-center gap-2"
                  disabled={ticktickStatus === "checking"}
                >
                  <LinkIcon className="h-4 w-4" />
                  Connect TickTick
                </Button>
              )}
            </div>
          </div>

          <Alert className="border-blue-200 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/20">
            <Info className="h-4 w-4 text-blue-400" />
            <AlertDescription className="text-sm text-muted-foreground">
              After connecting, you can sync your TickTick tasks from the Analyze tab.
              All tasks will be automatically analyzed by AI.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Personal Context</CardTitle>
          <CardDescription>
            Share concise details to help the LLM personalize analysis (kept short for 4B models)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">People & roles</label>
              <Textarea
                placeholder={"Sam (manager)\nAlex (partner)"}
                value={peopleText}
                onChange={(e) => setPeopleText(e.target.value)}
                rows={4}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Pets</label>
              <Textarea
                placeholder={"Ari (cat)"}
                value={petsText}
                onChange={(e) => setPetsText(e.target.value)}
                rows={4}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Activities</label>
            <Textarea
              placeholder={"Climbing Tue/Thu\nYoga Sat"}
              value={activitiesText}
              onChange={(e) => setActivitiesText(e.target.value)}
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Notes</label>
            <Textarea
              placeholder="Morning focus time, prefers async updates"
              value={notesText}
              onChange={(e) => setNotesText(e.target.value)}
              rows={3}
            />
          </div>

          <div className="flex items-center gap-3">
            <Button onClick={saveProfile} disabled={profileSaving || profileLoading}>
              {profileSaving ? "Saving..." : "Save personal context"}
            </Button>
            {profileMessage && <span className="text-sm text-gray-300">{profileMessage}</span>}
            {profileLoading && <span className="text-xs text-gray-400">Loading...</span>}
          </div>
          <p className="text-xs text-muted-foreground">
            We store this securely and send a compressed summary with each analysis. Keep it brief for best results.
          </p>
        </CardContent>
      </Card>

      <Card className="border-blue-200 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Info className="h-5 w-5 text-blue-400" />
            Architecture Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground space-y-2">
            <p>Your requests flow through these components:</p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Frontend (Next.js) sends task to backend</li>
              <li>Backend (FastAPI) receives request</li>
              <li>Backend connects to Ollama for LLM analysis</li>
              <li>Results return to frontend for display</li>
            </ol>
            <p className="mt-3 text-xs">
              The frontend never communicates directly with Ollama - all AI requests go through your backend for security and flexibility.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
