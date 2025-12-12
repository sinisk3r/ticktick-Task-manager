"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2, XCircle, Loader2, Info, Link as LinkIcon, Unlink, ExternalLink } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { API_BASE } from "@/lib/api"

export function TickTickSettings() {
  const [ticktickConnected, setTicktickConnected] = useState(false)
  const [ticktickUserId, setTicktickUserId] = useState<string | null>(null)
  const [ticktickStatus, setTicktickStatus] = useState<"checking" | "ready">("ready")
  const [saveMessage, setSaveMessage] = useState<string>("")
  const [backendUrl] = useState(API_BASE)

  useEffect(() => {
    checkTicktickStatus()
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

  return (
    <div className="space-y-6">
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

          {saveMessage && (
            <Alert className="border-green-200 bg-green-50 dark:border-green-700 dark:bg-green-900/20">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <AlertDescription className="text-green-600 dark:text-green-400">
                {saveMessage}
              </AlertDescription>
            </Alert>
          )}

          <Alert className="border-blue-200 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/20">
            <Info className="h-4 w-4 text-blue-400" />
            <AlertDescription className="text-sm text-muted-foreground">
              After connecting, you can sync your TickTick tasks from the Analyze tab.
              All tasks will be automatically analyzed by AI.
            </AlertDescription>
          </Alert>

          <div className="space-y-3 p-3 bg-muted/30 rounded-md border border-border">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Info className="h-4 w-4 flex-shrink-0" />
              <span>Manage your TickTick OAuth apps:</span>
              <a
                href="https://developer.ticktick.com/manage"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 inline-flex items-center gap-1 hover:underline"
              >
                Developer Console
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Required Redirect URI:</p>
              <div className="flex items-center gap-2 p-2 bg-background rounded border border-border">
                <code className="text-xs text-foreground flex-1">
                  {backendUrl}/auth/ticktick/callback
                </code>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 px-2 text-xs"
                  onClick={() => {
                    navigator.clipboard.writeText(`${backendUrl}/auth/ticktick/callback`)
                    setSaveMessage("Redirect URI copied to clipboard!")
                    setTimeout(() => setSaveMessage(""), 2000)
                  }}
                >
                  Copy
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Add this exact URI to your TickTick OAuth app settings
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
