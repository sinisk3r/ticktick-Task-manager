"use client"

import { useState } from "react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Eye, Edit } from "lucide-react"
import { cn } from "@/lib/utils"

interface MarkdownEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  minRows?: number
}

export function MarkdownEditor({
  value,
  onChange,
  placeholder = "Add a description...",
  disabled,
  minRows = 4,
}: MarkdownEditorProps) {
  const [isPreview, setIsPreview] = useState(false)

  // Simple markdown renderer (can be enhanced with a library like react-markdown)
  const renderMarkdown = (text: string) => {
    return text
      .split("\n")
      .map((line, i) => {
        // Headers
        if (line.startsWith("### ")) {
          return (
            <h3 key={i} className="text-lg font-semibold mt-2 mb-1">
              {line.replace("### ", "")}
            </h3>
          )
        }
        if (line.startsWith("## ")) {
          return (
            <h2 key={i} className="text-xl font-bold mt-3 mb-2">
              {line.replace("## ", "")}
            </h2>
          )
        }
        if (line.startsWith("# ")) {
          return (
            <h1 key={i} className="text-2xl font-bold mt-4 mb-2">
              {line.replace("# ", "")}
            </h1>
          )
        }
        // Bold
        const boldText = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        const italicText = boldText.replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Lists
        if (line.startsWith("- ") || line.startsWith("* ")) {
          return (
            <li key={i} className="ml-4" dangerouslySetInnerHTML={{ __html: italicText.replace(/^[-*] /, "") }} />
          )
        }
        // Code
        const codeText = italicText.replace(/`(.*?)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-sm">$1</code>')

        return line ? (
          <p key={i} className="mb-2" dangerouslySetInnerHTML={{ __html: codeText }} />
        ) : (
          <br key={i} />
        )
      })
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <label className="text-sm text-muted-foreground">Description</label>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsPreview(!isPreview)}
          className="h-7 text-xs"
          disabled={disabled}
        >
          {isPreview ? (
            <>
              <Edit className="h-3 w-3 mr-1" />
              Edit
            </>
          ) : (
            <>
              <Eye className="h-3 w-3 mr-1" />
              Preview
            </>
          )}
        </Button>
      </div>

      {isPreview ? (
        <div
          className={cn(
            "min-h-[100px] p-3 rounded-md border bg-muted/50 text-sm prose prose-sm dark:prose-invert max-w-none",
            !value && "text-muted-foreground italic"
          )}
        >
          {value ? renderMarkdown(value) : "No description"}
        </div>
      ) : (
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          rows={minRows}
          className="resize-none"
        />
      )}

      <p className="text-xs text-muted-foreground">
        Supports markdown: **bold**, *italic*, `code`, # headers, - lists
      </p>
    </div>
  )
}
