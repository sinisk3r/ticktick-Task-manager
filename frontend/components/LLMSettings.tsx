"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CheckCircle2, XCircle, Loader2, Info } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

export function LLMSettings() {
  const [selectedModel, setSelectedModel] = useState("qwen3:4b")
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "disconnected" | "testing">("disconnected")
  const [statusMessage, setStatusMessage] = useState<string>("")
  const [saveMessage, setSaveMessage] = useState<string>("")
  const [backendUrl] = useState("http://127.0.0.1:8000")

  // Load settings and fetch available models on mount
  useEffect(() => {
    const savedModel = localStorage.getItem("llm_model")
    if (savedModel) setSelectedModel(savedModel)

    // Fetch available models and test connection
    fetchModels()
  }, [])

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
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
    }
  }

  const getStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "border-green-700 bg-green-900/50"
      case "disconnected":
        return "border-red-700 bg-red-900/50"
      case "testing":
        return "border-blue-700 bg-blue-900/50"
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
              <div className="p-3 bg-gray-900/50 rounded-md border border-gray-700">
                <code className="text-sm text-gray-300">{backendUrl}</code>
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
              <Alert className="border-green-700 bg-green-900/50">
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

      <Card className="border-blue-700 bg-blue-900/20">
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
