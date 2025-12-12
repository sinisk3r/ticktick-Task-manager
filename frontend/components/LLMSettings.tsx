"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CheckCircle2, XCircle, Loader2, Info } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { settingsAPI, LLMProvider, Settings, SettingsUpdate } from "@/lib/api"

export function LLMSettings() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const [formData, setFormData] = useState<SettingsUpdate>({
    llm_provider: 'ollama',
    llm_model: '',
    llm_api_key: '',
    llm_base_url: '',
    llm_temperature: 0.2,
    llm_max_tokens: 1000,
  })

  // TODO: Get actual user ID from auth context
  const userId = 1

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await settingsAPI.getSettings(userId)
      setSettings(data)

      // Populate form with loaded settings
      setFormData({
        llm_provider: data.llm_provider,
        llm_model: data.llm_model || '',
        llm_api_key: data.llm_api_key || '',
        llm_base_url: data.llm_base_url || '',
        llm_temperature: data.llm_temperature || 0.2,
        llm_max_tokens: data.llm_max_tokens || 1000,
      })
    } catch (err: any) {
      setError(err.message || 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(false)

      // Send all form data (API will handle what changed)
      const updated = await settingsAPI.updateSettings(userId, formData)
      setSettings(updated)
      setSuccess(true)

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000)
    } catch (err: any) {
      setError(err.message || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  // Provider-specific configuration helpers
  const getProviderHint = (provider: LLMProvider): string => {
    switch (provider) {
      case 'ollama':
        return 'Local Ollama instance (e.g., qwen3:8b, llama3:8b)'
      case 'openrouter':
        return 'OpenRouter model (e.g., nex-agi/deepseek-v3.1-nex-n1:free)'
      case 'anthropic':
        return 'Anthropic Claude model (e.g., claude-sonnet-4)'
      case 'openai':
        return 'OpenAI model (e.g., gpt-4-turbo, gpt-3.5-turbo)'
      case 'gemini':
        return 'Google Gemini model (coming soon)'
      default:
        return ''
    }
  }

  const requiresApiKey = (provider: LLMProvider): boolean => {
    return provider !== 'ollama'
  }

  const requiresBaseUrl = (provider: LLMProvider): boolean => {
    return provider === 'ollama'
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-12">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading settings...
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>LLM Provider Configuration</CardTitle>
          <CardDescription>
            Configure your AI model preferences for the task copilot. Settings are applied immediately.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <Alert className="border-red-200 bg-red-50 dark:border-red-700 dark:bg-red-900/20">
              <XCircle className="h-4 w-4 text-red-500" />
              <AlertDescription className="text-red-600 dark:text-red-400">
                {error}
              </AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="border-green-200 bg-green-50 dark:border-green-700 dark:bg-green-900/20">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <AlertDescription className="text-green-600 dark:text-green-400">
                Settings saved successfully! Changes will apply to all new requests.
              </AlertDescription>
            </Alert>
          )}

          {/* Provider Selection */}
          <div className="space-y-2">
            <Label htmlFor="provider">LLM Provider</Label>
            <Select
              value={formData.llm_provider}
              onValueChange={(value: LLMProvider) =>
                setFormData({ ...formData, llm_provider: value })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ollama">Ollama (Local)</SelectItem>
                <SelectItem value="openrouter">OpenRouter</SelectItem>
                <SelectItem value="anthropic">Anthropic Claude</SelectItem>
                <SelectItem value="openai">OpenAI</SelectItem>
                <SelectItem value="gemini" disabled>Gemini (Coming Soon)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Choose which AI provider to use for task analysis and chat
            </p>
          </div>

          {/* Model Name */}
          <div className="space-y-2">
            <Label htmlFor="model">Model Name</Label>
            <Input
              id="model"
              value={formData.llm_model || ''}
              onChange={(e) =>
                setFormData({ ...formData, llm_model: e.target.value })
              }
              placeholder={getProviderHint(formData.llm_provider as LLMProvider)}
            />
            <p className="text-xs text-muted-foreground">
              {getProviderHint(formData.llm_provider as LLMProvider)}
            </p>
          </div>

          {/* API Key (for cloud providers) */}
          {requiresApiKey(formData.llm_provider as LLMProvider) && (
            <div className="space-y-2">
              <Label htmlFor="api-key">API Key</Label>
              <Input
                id="api-key"
                type="password"
                value={formData.llm_api_key || ''}
                onChange={(e) =>
                  setFormData({ ...formData, llm_api_key: e.target.value })
                }
                placeholder="sk-..."
              />
              <p className="text-xs text-muted-foreground">
                Your API key is encrypted and stored securely
              </p>
            </div>
          )}

          {/* Base URL (for Ollama) */}
          {requiresBaseUrl(formData.llm_provider as LLMProvider) && (
            <div className="space-y-2">
              <Label htmlFor="base-url">Base URL</Label>
              <Input
                id="base-url"
                value={formData.llm_base_url || ''}
                onChange={(e) =>
                  setFormData({ ...formData, llm_base_url: e.target.value })
                }
                placeholder="http://localhost:11434"
              />
              <p className="text-xs text-muted-foreground">
                URL of your Ollama instance
              </p>
            </div>
          )}

          {/* Temperature */}
          <div className="space-y-2">
            <Label htmlFor="temperature">
              Temperature: {formData.llm_temperature?.toFixed(1)}
            </Label>
            <Input
              id="temperature"
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={formData.llm_temperature || 0.2}
              onChange={(e) =>
                setFormData({ ...formData, llm_temperature: parseFloat(e.target.value) })
              }
            />
            <p className="text-xs text-muted-foreground">
              Lower values (0.0-0.5) for focused responses, higher values (0.5-2.0) for creative responses
            </p>
          </div>

          {/* Max Tokens */}
          <div className="space-y-2">
            <Label htmlFor="max-tokens">Max Tokens</Label>
            <Input
              id="max-tokens"
              type="number"
              min="1"
              max="100000"
              value={formData.llm_max_tokens || 1000}
              onChange={(e) =>
                setFormData({ ...formData, llm_max_tokens: parseInt(e.target.value) })
              }
            />
            <p className="text-xs text-muted-foreground">
              Maximum number of tokens to generate per response
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <Button
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
            <Button
              onClick={loadSettings}
              variant="outline"
              disabled={loading || saving}
            >
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

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
