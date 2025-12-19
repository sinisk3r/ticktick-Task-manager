'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { EnhancedSuggestion } from '@/types/task'
import { Sparkles, Check, X } from 'lucide-react'

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
  const [accepted, setAccepted] = useState<Set<number>>(new Set())
  const [rejected, setRejected] = useState<Set<number>>(new Set())
  const [applying, setApplying] = useState(false)

  const handleAccept = async (idx: number) => {
    setApplying(true)
    try {
      // Apply this single suggestion
      await onApply([suggestions[idx]])
      // Mark as accepted
      const newAccepted = new Set(accepted)
      newAccepted.add(idx)
      setAccepted(newAccepted)
    } finally {
      setApplying(false)
    }
  }

  const handleReject = (idx: number) => {
    const newRejected = new Set(rejected)
    newRejected.add(idx)
    setRejected(newRejected)
  }

  const handleAcceptAll = async () => {
    setApplying(true)
    try {
      // Apply all remaining suggestions (not already accepted or rejected)
      const remainingSuggestions = suggestions.filter(
        (_, idx) => !accepted.has(idx) && !rejected.has(idx)
      )
      await onApply(remainingSuggestions)
      // Mark all as accepted
      const newAccepted = new Set(accepted)
      remainingSuggestions.forEach((_, idx) => {
        const originalIdx = suggestions.indexOf(suggestions.find((s) => s === remainingSuggestions[idx])!)
        newAccepted.add(originalIdx)
      })
      setAccepted(newAccepted)
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

  // Count remaining suggestions
  const remainingCount = suggestions.filter(
    (_, idx) => !accepted.has(idx) && !rejected.has(idx)
  ).length

  return (
    <Card className="p-4 bg-accent/5 border-accent animate-in fade-in slide-in-from-bottom-2">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="size-5 text-primary" />
          <h3 className="font-semibold">
            AI Suggestions ({remainingCount} remaining)
          </h3>
        </div>
        <div className="flex gap-2">
          <Button
            variant="default"
            size="sm"
            onClick={handleAcceptAll}
            disabled={applying || remainingCount === 0}
            className="text-xs gap-1"
          >
            <Check className="size-3" />
            Accept All
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            disabled={applying}
            className="text-xs"
          >
            Dismiss
          </Button>
        </div>
      </div>

      <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
        {Object.entries(groupedSuggestions).map(([fieldType, items]) => (
          <div key={fieldType} className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground capitalize">
              {fieldType.replace(/_/g, ' ')} {items.length > 1 && `(${items.length} options)`}
            </h4>

            {items.map((suggestion) => {
              const isAccepted = accepted.has(suggestion.idx)
              const isRejected = rejected.has(suggestion.idx)

              return (
                <div
                  key={suggestion.idx}
                  className={`p-3 rounded-lg border transition-all ${
                    isAccepted
                      ? 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800 opacity-60'
                      : isRejected
                      ? 'bg-muted/50 border-muted opacity-50'
                      : 'bg-card hover:bg-accent/5 border-border'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        {getConfidenceBadge(suggestion.confidence, suggestion.priority)}
                      </div>

                      <div className="text-sm mb-2">
                        {suggestion.current_display && (
                          <>
                            <span className="text-muted-foreground">Current: </span>
                            <span className="line-through">{suggestion.current_display}</span>
                            <span className="mx-2">→</span>
                          </>
                        )}
                        <span className={`font-medium ${isAccepted ? 'text-green-700 dark:text-green-400' : 'text-primary'}`}>
                          {suggestion.suggested_display}
                        </span>
                      </div>

                      <p className="text-xs text-muted-foreground italic">
                        {suggestion.reason}
                      </p>
                    </div>

                    <div className="flex gap-1 shrink-0">
                      {isAccepted ? (
                        <div className="flex items-center gap-1 text-xs text-green-700 dark:text-green-400 font-medium">
                          <Check className="size-4" />
                          Applied
                        </div>
                      ) : isRejected ? (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <X className="size-4" />
                          Skipped
                        </div>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleAccept(suggestion.idx)}
                            disabled={applying}
                            className="h-8 w-8 p-0 hover:bg-green-100 hover:text-green-700 dark:hover:bg-green-950"
                            title="Accept this suggestion"
                          >
                            <Check className="size-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleReject(suggestion.idx)}
                            disabled={applying}
                            className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-700 dark:hover:bg-red-950"
                            title="Reject this suggestion"
                          >
                            <X className="size-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </Card>
  )
}
