"use client"

import { LLMConfigurationManager } from "./LLMConfigurationManager"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Info } from "lucide-react"

export function LLMSettings() {
  return (
    <div className="space-y-6">
      {/* Main Configuration Manager */}
      <LLMConfigurationManager />

      {/* Info Section */}
      <Card className="border-blue-200 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Info className="h-5 w-5 text-blue-400" />
            Quick Start Guide
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm text-muted-foreground">
            <div>
              <strong className="text-foreground">Ollama (Free):</strong>
              <p className="text-xs mt-1">Run AI models locally. Install from{' '}
                <a href="https://ollama.ai" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                  ollama.ai
                </a>
              </p>
            </div>
            <div>
              <strong className="text-foreground">OpenRouter:</strong>
              <p className="text-xs mt-1">Access multiple AI models with one API key. Sign up at{' '}
                <a href="https://openrouter.ai" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                  openrouter.ai
                </a>
              </p>
            </div>
            <div>
              <strong className="text-foreground">Anthropic Claude:</strong>
              <p className="text-xs mt-1">Use Claude models directly. Get API key from{' '}
                <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                  console.anthropic.com
                </a>
              </p>
            </div>
            <div>
              <strong className="text-foreground">OpenAI:</strong>
              <p className="text-xs mt-1">Access GPT models. Get API key from{' '}
                <a href="https://platform.openai.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                  platform.openai.com
                </a>
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}