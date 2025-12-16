'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Card } from '@/components/ui/card'
import { EnhancedSuggestion } from '@/types/task'
import { Sparkles, CheckCircle2 } from 'lucide-react'

interface EnhancedSuggestionPanelProps {
  suggestions: EnhancedSuggestion[]
  onApply: (selected: EnhancedSuggestion[]) => Promise<void>
  onDismiss: () => void
}

export function EnhancedSuggestionPanel({
  suggestions,
  onApply,
  onDismiss,
}: EnhancedSuggestionPanelProps) {
  const [selected, setSelected] = useState<Set<number>>(
    // Default: Select high-confidence suggestions (≥0.85)
    new Set(
      suggestions
        .map((_, idx) => idx)
        .filter(idx => suggestions[idx].confidence >= 0.85)
    )
  )
  const [applying, setApplying] = useState(false)

  const toggleSelection = (idx: number) => {
    const newSelected = new Set(selected)
    if (newSelected.has(idx)) {
      newSelected.delete(idx)
    } else {
      newSelected.add(idx)
    }
    setSelected(newSelected)
  }

  const selectAll = () => {
    setSelected(new Set(suggestions.map((_, idx) => idx)))
  }

  const deselectAll = () => {
    setSelected(new Set())
  }

  const handleApply = async () => {
    setApplying(true)
    try {
      const selectedSuggestions = suggestions.filter((_, idx) =>
        selected.has(idx)
      )
      await onApply(selectedSuggestions)
    } finally {
      setApplying(false)
    }
  }

  const getConfidenceBadge = (confidence: number, priority: string) => {
    const colors = {
      high: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      medium: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      low: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    }

    return (
      <Badge
        variant="outline"
        className={`text-xs ${colors[priority as keyof typeof colors]}`}
      >
        {Math.round(confidence * 100)}% confident
      </Badge>
    )
  }

  // Group suggestions by field type
  const groupedSuggestions = suggestions.reduce((acc, s, idx) => {
    if (!acc[s.type]) acc[s.type] = []
    acc[s.type].push({ ...s, idx })
    return acc
  }, {} as Record<string, (EnhancedSuggestion & { idx: number })[]>)

  return (
    <Card className="p-4 bg-accent/5 border-accent animate-in fade-in slide-in-from-bottom-2">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="size-5 text-primary" />
          <h3 className="font-semibold">
            AI Suggestions ({suggestions.length})
          </h3>
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={selectAll}
            className="text-xs"
          >
            Select All
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={deselectAll}
            className="text-xs"
          >
            Clear
          </Button>
        </div>
      </div>

      <div className="space-y-4 max-h-[400px] overflow-y-auto">
        {Object.entries(groupedSuggestions).map(([fieldType, items]) => (
          <div key={fieldType} className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground capitalize">
              {fieldType.replace(/_/g, ' ')} {items.length > 1 && `(${items.length} options)`}
            </h4>

            {items.map((suggestion) => (
              <div
                key={suggestion.idx}
                className={`p-3 rounded-lg border transition-colors cursor-pointer ${
                  selected.has(suggestion.idx)
                    ? 'bg-primary/10 border-primary'
                    : 'bg-card hover:bg-accent/5'
                }`}
                onClick={() => toggleSelection(suggestion.idx)}
              >
                <div className="flex items-start gap-3">
                  <Checkbox
                    checked={selected.has(suggestion.idx)}
                    onCheckedChange={() => toggleSelection(suggestion.idx)}
                    className="mt-1"
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      {getConfidenceBadge(suggestion.confidence, suggestion.priority)}
                      {suggestion.priority === 'high' && (
                        <CheckCircle2 className="size-3 text-green-600" />
                      )}
                    </div>

                    <div className="text-sm mb-2">
                      {suggestion.current_display && (
                        <>
                          <span className="text-muted-foreground">Current: </span>
                          <span className="line-through">{suggestion.current_display}</span>
                          <span className="mx-2">→</span>
                        </>
                      )}
                      <span className="font-medium text-primary">
                        {suggestion.suggested_display}
                      </span>
                    </div>

                    <p className="text-xs text-muted-foreground italic">
                      {suggestion.reason}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="flex gap-2 mt-4 pt-3 border-t">
        <Button
          onClick={handleApply}
          disabled={applying || selected.size === 0}
          className="flex-1 gap-2"
        >
          <Sparkles className="size-4" />
          {applying
            ? 'Applying...'
            : `Apply ${selected.size} suggestion${selected.size !== 1 ? 's' : ''}`}
        </Button>
        <Button
          variant="outline"
          onClick={onDismiss}
          disabled={applying}
        >
          Dismiss
        </Button>
      </div>
    </Card>
  )
}
