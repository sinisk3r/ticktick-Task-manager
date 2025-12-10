"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2, XCircle, Loader2 } from "lucide-react"

export function LLMSettings() {
  const [providerUrl, setProviderUrl] = useState("http://127.0.0.1:11434")
  const [model, setModel] = useState("qwen3:4b")
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "disconnected" | "testing">("disconnected")
  const [statusMessage, setStatusMessage] = useState<string>("")
  const [saveMessage, setSaveMessage] = useState<string>("")

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedUrl = localStorage.getItem("llm_provider_url")
    const savedModel = localStorage.getItem("llm_model")

    if (savedUrl) setProviderUrl(savedUrl)
    if (savedModel) setModel(savedModel)

    // Auto-test connection on mount if settings exist
    if (savedUrl) {
      testConnection()
    }
  }, [])

  const testConnection = async () => {
    setConnectionStatus("testing")
    setStatusMessage("Testing connection...")

    try {
      const response = await fetch("http://localhost:8000/api/llm/health", {
        method: "GET",
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (data.status === "healthy") {
        setConnectionStatus("connected")
        setStatusMessage(`Connected to ${data.provider} - Model: ${data.model}`)
      } else {
        setConnectionStatus("disconnected")
        setStatusMessage(data.message || "Connection failed")
      }
    } catch (err) {
      setConnectionStatus("disconnected")
      setStatusMessage(
        err instanceof Error
          ? err.message
          : "Failed to connect. Make sure the backend and Ollama are running."
      )
    }
  }

  const saveSettings = () => {
    localStorage.setItem("llm_provider_url", providerUrl)
    localStorage.setItem("llm_model", model)
    setSaveMessage("Settings saved successfully!")

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
        return "bg-green-900/50 border-green-700"
      case "disconnected":
        return "bg-red-900/50 border-red-700"
      case "testing":
        return "bg-blue-900/50 border-blue-700"
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>LLM Provider Settings</CardTitle>
          <CardDescription>
            Configure your Ollama instance for task analysis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="provider-url" className="text-sm font-medium text-gray-300">
              Ollama Provider URL
            </label>
            <Input
              id="provider-url"
              type="text"
              placeholder="http://127.0.0.1:11434"
              value={providerUrl}
              onChange={(e) => setProviderUrl(e.target.value)}
            />
            <p className="text-xs text-gray-500">
              The URL where your Ollama instance is running
            </p>
          </div>

          <div className="space-y-2">
            <label htmlFor="model" className="text-sm font-medium text-gray-300">
              Model Name
            </label>
            <Input
              id="model"
              type="text"
              placeholder="qwen3:4b"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
            <p className="text-xs text-gray-500">
              The name of the Ollama model to use (e.g., qwen3:4b, llama2, mistral)
            </p>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={testConnection}
              disabled={connectionStatus === "testing"}
              variant="outline"
              className="flex-1"
            >
              {connectionStatus === "testing" ? "Testing..." : "Test Connection"}
            </Button>

            <Button
              onClick={saveSettings}
              className="flex-1"
            >
              Save Settings
            </Button>
          </div>

          {saveMessage && (
            <div className="rounded-md bg-green-900/50 border border-green-700 p-4">
              <p className="text-sm text-green-200">{saveMessage}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className={getStatusColor()}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {getStatusIcon()}
            <span>Connection Status</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-300">Status:</span>
              <span className="text-sm capitalize">{connectionStatus}</span>
            </div>
            {statusMessage && (
              <div className="text-sm text-gray-200 bg-gray-900/50 p-3 rounded-md">
                {statusMessage}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gray-800/50">
        <CardHeader>
          <CardTitle className="text-base">Quick Start Guide</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal list-inside space-y-2 text-sm text-gray-300">
            <li>Install Ollama from <span className="text-blue-400">https://ollama.ai</span></li>
            <li>Run: <code className="bg-gray-900 px-2 py-1 rounded text-blue-300">ollama pull qwen3:4b</code></li>
            <li>Ensure Ollama is running (it starts automatically on install)</li>
            <li>Click "Test Connection" to verify setup</li>
          </ol>
        </CardContent>
      </Card>
    </div>
  )
}
