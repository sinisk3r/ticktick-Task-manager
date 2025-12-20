"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, XCircle, Loader2, Plus, Edit, Trash2, TestTube, Settings, AlertCircle } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { llmConfigAPI, settingsAPI, LLMConfiguration, LLMConfigurationCreate, LLMConfigurationUpdate, LLMProvider, ConnectionTestResult, EnvDefaultsResponse } from "@/lib/api"

export function LLMConfigurationManager() {
  const [configurations, setConfigurations] = useState<LLMConfiguration[]>([])
  const [activeConfigId, setActiveConfigId] = useState<number | null>(null)
  const [envDefaults, setEnvDefaults] = useState<EnvDefaultsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Dialog states
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editingConfig, setEditingConfig] = useState<LLMConfiguration | null>(null)

  // Form states
  const [formData, setFormData] = useState<LLMConfigurationCreate>({
    name: "",
    provider: "ollama",
    model: "",
    api_key: "",
    base_url: "",
    temperature: 0.2,
    max_tokens: 1000,
    is_default: false
  })

  // Operation states
  const [saving, setSaving] = useState(false)
  const [testingConnections, setTestingConnections] = useState<Set<number>>(new Set())
  const [testResults, setTestResults] = useState<Map<number, ConnectionTestResult>>(new Map())

  // TODO: Get actual user ID from auth context
  const userId = 1

  // Load configurations and settings on mount
  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Load configurations, settings, and env defaults in parallel
      const [configsData, settingsData, defaultsData] = await Promise.all([
        llmConfigAPI.listConfigurations(userId),
        settingsAPI.getSettings(userId),
        llmConfigAPI.getEnvDefaults()
      ])

      setConfigurations(configsData)
      setActiveConfigId(settingsData.active_llm_config_id ?? null)
      setEnvDefaults(defaultsData)
    } catch (err: any) {
      setError(err.message || 'Failed to load configurations')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateConfig = async () => {
    try {
      setSaving(true)
      setError(null)

      const newConfig = await llmConfigAPI.createConfiguration(userId, formData)

      // Refresh the list
      await loadData()

      // Close dialog and reset form
      setIsCreateDialogOpen(false)
      resetForm()
    } catch (err: any) {
      setError(err.message || 'Failed to create configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleEditConfig = async () => {
    if (!editingConfig) return

    try {
      setSaving(true)
      setError(null)

      const updateData: LLMConfigurationUpdate = {
        name: formData.name,
        provider: formData.provider,
        model: formData.model,
        api_key: formData.api_key || undefined,
        base_url: formData.base_url || undefined,
        temperature: formData.temperature,
        max_tokens: formData.max_tokens,
        is_default: formData.is_default
      }

      await llmConfigAPI.updateConfiguration(editingConfig.id, userId, updateData)

      // Refresh the list
      await loadData()

      // Close dialog and reset form
      setIsEditDialogOpen(false)
      setEditingConfig(null)
      resetForm()
    } catch (err: any) {
      setError(err.message || 'Failed to update configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteConfig = async (configId: number) => {
    if (!confirm('Are you sure you want to delete this configuration?')) return

    try {
      setError(null)
      await llmConfigAPI.deleteConfiguration(configId, userId)
      await loadData()
    } catch (err: any) {
      setError(err.message || 'Failed to delete configuration')
    }
  }

  const handleTestConnection = async (configId: number) => {
    try {
      setTestingConnections(prev => new Set(prev).add(configId))

      const result = await llmConfigAPI.testConnection(configId, userId)
      setTestResults(prev => new Map(prev).set(configId, result))

      // Refresh to get updated connection status
      await loadData()
    } catch (err: any) {
      setError(err.message || 'Failed to test connection')
    } finally {
      setTestingConnections(prev => {
        const newSet = new Set(prev)
        newSet.delete(configId)
        return newSet
      })
    }
  }

  const handleSetActive = async (configId: number) => {
    try {
      setError(null)
      await settingsAPI.updateSettings(userId, { active_llm_config_id: configId })
      setActiveConfigId(configId)
    } catch (err: any) {
      setError(err.message || 'Failed to set active configuration')
    }
  }

  const openEditDialog = (config: LLMConfiguration) => {
    setEditingConfig(config)
    setFormData({
      name: config.name,
      provider: config.provider,
      model: config.model,
      api_key: "", // Don't pre-fill API key for security
      base_url: config.base_url || "",
      temperature: config.temperature,
      max_tokens: config.max_tokens,
      is_default: config.is_default
    })
    setIsEditDialogOpen(true)
  }

  const resetForm = () => {
    setFormData({
      name: "",
      provider: "ollama",
      model: "",
      api_key: "",
      base_url: "",
      temperature: 0.2,
      max_tokens: 1000,
      is_default: false
    })
  }

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
        return 'Google Gemini model (e.g., gemini-2.0-flash, gemini-pro)'
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

  const hasEnvApiKey = (provider: LLMProvider): boolean => {
    return envDefaults?.providers[provider]?.has_api_key ?? false
  }

  const getEnvDefaultsForProvider = (provider: LLMProvider) => {
    return envDefaults?.providers[provider]
  }

  const handleProviderChange = (provider: LLMProvider) => {
    const defaults = getEnvDefaultsForProvider(provider)
    setFormData({
      ...formData,
      provider,
      model: defaults?.model || "",
      base_url: defaults?.base_url || (provider === 'ollama' ? 'http://localhost:11434' : ""),
      // Clear API key when switching providers
      api_key: ""
    })
  }

  const getConnectionStatusBadge = (config: LLMConfiguration) => {
    const isActive = config.id === activeConfigId
    const isTesting = testingConnections.has(config.id)

    if (isTesting) {
      return <Badge variant="secondary"><Loader2 className="h-3 w-3 mr-1 animate-spin" />Testing</Badge>
    }

    switch (config.connection_status) {
      case 'success':
        return <Badge variant="default" className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" />Connected</Badge>
      case 'failed':
        return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Failed</Badge>
      default:
        return <Badge variant="secondary">Untested</Badge>
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-12">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading configurations...
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>LLM Provider Configurations</CardTitle>
          <CardDescription>
            Manage your saved AI model configurations. Create multiple configurations and switch between them easily.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Environment Configuration Info */}
          {envDefaults && (
            <Alert className="border-blue-200 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/20">
              <Settings className="h-4 w-4 text-blue-500" />
              <AlertDescription className="text-blue-600 dark:text-blue-400">
                <div className="space-y-1">
                  <p className="font-medium">Environment Configuration</p>
                  <p className="text-xs">
                    Default provider: <strong>{envDefaults.active_provider}</strong> |
                    Available API keys: {' '}
                    {Object.entries(envDefaults.providers)
                      .filter(([, p]) => p.has_api_key || p.provider === 'ollama')
                      .map(([name]) => name)
                      .join(', ') || 'none'}
                  </p>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {error && (
            <Alert className="border-red-200 bg-red-50 dark:border-red-700 dark:bg-red-900/20">
              <AlertCircle className="h-4 w-4 text-red-500" />
              <AlertDescription className="text-red-600 dark:text-red-400">
                {error}
              </AlertDescription>
            </Alert>
          )}

          {/* Configuration List */}
          <div className="space-y-4">
            {configurations.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Settings className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No configurations found. Create your first configuration to get started.</p>
              </div>
            ) : (
              configurations.map((config) => (
                <div
                  key={config.id}
                  className={`border rounded-lg p-4 space-y-3 ${config.id === activeConfigId ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200'
                    }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <h3 className="font-medium">{config.name}</h3>
                      {config.id === activeConfigId && (
                        <Badge variant="default" className="bg-blue-500">Active</Badge>
                      )}
                      {getConnectionStatusBadge(config)}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleTestConnection(config.id)}
                        disabled={testingConnections.has(config.id)}
                      >
                        <TestTube className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => openEditDialog(config)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDeleteConfig(config.id)}
                        disabled={config.id === activeConfigId}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="text-sm text-muted-foreground">
                    <p><strong>Provider:</strong> {config.provider} | <strong>Model:</strong> {config.model}</p>
                    {config.base_url && <p><strong>URL:</strong> {config.base_url}</p>}
                    {config.connection_error && (
                      <p className="text-red-500"><strong>Error:</strong> {config.connection_error}</p>
                    )}
                  </div>

                  {config.id !== activeConfigId && (
                    <Button
                      size="sm"
                      onClick={() => handleSetActive(config.id)}
                      className="w-full"
                    >
                      Set as Active
                    </Button>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Add Configuration Button */}
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button className="w-full">
                <Plus className="h-4 w-4 mr-2" />
                Add Configuration
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Add LLM Configuration</DialogTitle>
                <DialogDescription>
                  Create a new AI model configuration that you can switch to later.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                {/* Configuration Name */}
                <div className="space-y-2">
                  <Label htmlFor="name">Configuration Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Local Ollama, OpenRouter GPT-4"
                  />
                </div>

                {/* Provider Selection */}
                <div className="space-y-2">
                  <Label htmlFor="provider">Provider</Label>
                  <Select
                    value={formData.provider}
                    onValueChange={(value: LLMProvider) => handleProviderChange(value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ollama">
                        Ollama (Local)
                      </SelectItem>
                      <SelectItem value="openrouter">
                        OpenRouter {hasEnvApiKey('openrouter') && <span className="text-green-500 ml-1">✓ key</span>}
                      </SelectItem>
                      <SelectItem value="anthropic">
                        Anthropic Claude {hasEnvApiKey('anthropic') && <span className="text-green-500 ml-1">✓ key</span>}
                      </SelectItem>
                      <SelectItem value="openai">
                        OpenAI {hasEnvApiKey('openai') && <span className="text-green-500 ml-1">✓ key</span>}
                      </SelectItem>
                      <SelectItem value="gemini">
                        Google Gemini {hasEnvApiKey('gemini') && <span className="text-green-500 ml-1">✓ key</span>}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Model Name */}
                <div className="space-y-2">
                  <Label htmlFor="model">Model Name</Label>
                  <Input
                    id="model"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    placeholder={getProviderHint(formData.provider)}
                  />
                  <p className="text-xs text-muted-foreground">
                    {getProviderHint(formData.provider)}
                  </p>
                </div>

                {/* API Key (for cloud providers) */}
                {requiresApiKey(formData.provider) && (
                  <div className="space-y-2">
                    <Label htmlFor="api-key">
                      API Key
                      {hasEnvApiKey(formData.provider) && (
                        <span className="text-green-500 text-xs ml-2">(env key available)</span>
                      )}
                    </Label>
                    <Input
                      id="api-key"
                      type="password"
                      value={formData.api_key}
                      onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                      placeholder={hasEnvApiKey(formData.provider) ? "Leave blank to use env key" : "sk-..."}
                    />
                    {hasEnvApiKey(formData.provider) && (
                      <p className="text-xs text-muted-foreground">
                        An API key is configured in the server environment. Leave this blank to use it.
                      </p>
                    )}
                  </div>
                )}

                {/* Base URL (for Ollama) */}
                {requiresBaseUrl(formData.provider) && (
                  <div className="space-y-2">
                    <Label htmlFor="base-url">Base URL</Label>
                    <Input
                      id="base-url"
                      value={formData.base_url}
                      onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                      placeholder="http://localhost:11434"
                    />
                  </div>
                )}

                {/* Temperature */}
                <div className="space-y-2">
                  <Label htmlFor="temperature">
                    Temperature: {formData.temperature?.toFixed(1)}
                  </Label>
                  <Input
                    id="temperature"
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={formData.temperature}
                    onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                  />
                </div>

                {/* Max Tokens */}
                <div className="space-y-2">
                  <Label htmlFor="max-tokens">Max Tokens</Label>
                  <Input
                    id="max-tokens"
                    type="number"
                    min="1"
                    max="100000"
                    value={formData.max_tokens}
                    onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })}
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-4">
                  <Button
                    onClick={handleCreateConfig}
                    disabled={saving || !formData.name || !formData.model}
                    className="flex-1"
                  >
                    {saving ? 'Creating...' : 'Create Configuration'}
                  </Button>
                  <Button
                    onClick={() => {
                      setIsCreateDialogOpen(false)
                      resetForm()
                    }}
                    variant="outline"
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          {/* Edit Configuration Dialog */}
          <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Edit Configuration</DialogTitle>
                <DialogDescription>
                  Update the configuration settings. Leave API key blank to keep the existing key.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                {/* Same form fields as create dialog */}
                <div className="space-y-2">
                  <Label htmlFor="edit-name">Configuration Name</Label>
                  <Input
                    id="edit-name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Local Ollama, OpenRouter GPT-4"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-provider">Provider</Label>
                  <Select
                    value={formData.provider}
                    onValueChange={(value: LLMProvider) => handleProviderChange(value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ollama">
                        Ollama (Local)
                      </SelectItem>
                      <SelectItem value="openrouter">
                        OpenRouter {hasEnvApiKey('openrouter') && <span className="text-green-500 ml-1">✓ key</span>}
                      </SelectItem>
                      <SelectItem value="anthropic">
                        Anthropic Claude {hasEnvApiKey('anthropic') && <span className="text-green-500 ml-1">✓ key</span>}
                      </SelectItem>
                      <SelectItem value="openai">
                        OpenAI {hasEnvApiKey('openai') && <span className="text-green-500 ml-1">✓ key</span>}
                      </SelectItem>
                      <SelectItem value="gemini">
                        Google Gemini {hasEnvApiKey('gemini') && <span className="text-green-500 ml-1">✓ key</span>}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-model">Model Name</Label>
                  <Input
                    id="edit-model"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    placeholder={getProviderHint(formData.provider)}
                  />
                </div>

                {requiresApiKey(formData.provider) && (
                  <div className="space-y-2">
                    <Label htmlFor="edit-api-key">
                      API Key (leave blank to keep existing)
                      {hasEnvApiKey(formData.provider) && (
                        <span className="text-green-500 text-xs ml-2">(env key available)</span>
                      )}
                    </Label>
                    <Input
                      id="edit-api-key"
                      type="password"
                      value={formData.api_key}
                      onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                      placeholder={hasEnvApiKey(formData.provider) ? "Leave blank to use env key" : "Leave blank to keep existing key"}
                    />
                    {hasEnvApiKey(formData.provider) && (
                      <p className="text-xs text-muted-foreground">
                        An API key is configured in the server environment. Leave blank to use it.
                      </p>
                    )}
                  </div>
                )}

                {requiresBaseUrl(formData.provider) && (
                  <div className="space-y-2">
                    <Label htmlFor="edit-base-url">Base URL</Label>
                    <Input
                      id="edit-base-url"
                      value={formData.base_url}
                      onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                      placeholder="http://localhost:11434"
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="edit-temperature">
                    Temperature: {formData.temperature?.toFixed(1)}
                  </Label>
                  <Input
                    id="edit-temperature"
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={formData.temperature}
                    onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-max-tokens">Max Tokens</Label>
                  <Input
                    id="edit-max-tokens"
                    type="number"
                    min="1"
                    max="100000"
                    value={formData.max_tokens}
                    onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })}
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <Button
                    onClick={handleEditConfig}
                    disabled={saving || !formData.name || !formData.model}
                    className="flex-1"
                  >
                    {saving ? 'Saving...' : 'Save Changes'}
                  </Button>
                  <Button
                    onClick={() => {
                      setIsEditDialogOpen(false)
                      setEditingConfig(null)
                      resetForm()
                    }}
                    variant="outline"
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  )
}


