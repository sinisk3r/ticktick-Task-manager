'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'

interface Suggestion {
  id: number
  type: string
  current: any
  suggested: any
  reason: string
  confidence: number
}

interface SuggestionPanelProps {
  suggestions: Suggestion[]
  onApprove: (types: string[]) => Promise<void>
  onReject: (types: string[]) => Promise<void>
}

export function SuggestionPanel({ suggestions, onApprove, onReject }: SuggestionPanelProps) {
  const [expanded, setExpanded] = useState(true)
  const [approving, setApproving] = useState(false)

  const handleApproveAll = async () => {
    setApproving(true)
    try {
      await onApprove(['all'])
    } finally {
      setApproving(false)
    }
  }

  const handleRejectAll = async () => {
    await onReject(['all'])
  }

  const handleApproveSingle = async (type: string) => {
    await onApprove([type])
  }

  const handleRejectSingle = async (type: string) => {
    await onReject([type])
  }

  const getDisplayValue = (suggestion: Suggestion, isCurrent: boolean) => {
    const value = isCurrent ? suggestion.current : suggestion.suggested

    switch (suggestion.type) {
      case 'priority':
        const labels: { [key: number]: string } = { 0: 'None', 1: 'Low', 3: 'Medium', 5: 'High' }
        return labels[value as keyof typeof labels] || value
      case 'tags':
        return Array.isArray(value) ? value.join(', ') : value
      case 'quadrant':
        return value
      case 'start_date':
        return value ? new Date(value).toLocaleDateString() : 'Not set'
      default:
        return JSON.stringify(value)
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600 dark:text-green-400'
    if (confidence >= 0.7) return 'text-blue-600 dark:text-blue-400'
    return 'text-yellow-600 dark:text-yellow-400'
  }

  return (
    <Card className="p-4 bg-accent/5 border-accent">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">⚡</span>
          <h3 className="font-semibold">AI Suggestions ({suggestions.length})</h3>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? '▼' : '▶'}
        </Button>
      </div>

      {expanded && (
        <div className="space-y-3">
          {suggestions.map((suggestion) => (
            <div
              key={suggestion.id}
              className="p-3 bg-card rounded-lg border"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="capitalize">
                      {suggestion.type.replace('_', ' ')}
                    </Badge>
                    <span className={`text-xs font-medium ${getConfidenceColor(suggestion.confidence)}`}>
                      {Math.round(suggestion.confidence * 100)}% confident
                    </span>
                  </div>

                  <div className="text-sm mb-2">
                    <span className="text-muted-foreground">Current: </span>
                    <span className="font-medium">{getDisplayValue(suggestion, true)}</span>
                    <span className="mx-2">→</span>
                    <span className="text-muted-foreground">Suggested: </span>
                    <span className="font-medium text-primary">{getDisplayValue(suggestion, false)}</span>
                  </div>

                  <p className="text-sm text-muted-foreground italic">
                    "{suggestion.reason}"
                  </p>
                </div>
              </div>

              <div className="flex gap-2 mt-3">
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => handleApproveSingle(suggestion.type)}
                >
                  ✓ Apply
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleRejectSingle(suggestion.type)}
                >
                  ✗ Dismiss
                </Button>
              </div>
            </div>
          ))}

          {/* Bulk Actions */}
          <div className="flex gap-2 pt-2 border-t">
            <Button
              variant="default"
              onClick={handleApproveAll}
              disabled={approving}
              className="flex-1"
            >
              {approving ? '⏳ Applying...' : '✓ Approve All'}
            </Button>
            <Button
              variant="outline"
              onClick={handleRejectAll}
              disabled={approving}
              className="flex-1"
            >
              ✗ Dismiss All
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}
