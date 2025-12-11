"use client"

import { useMemo, useState } from "react"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

interface TagsInputProps {
  value?: string[]
  onChange?: (tags: string[]) => void
  placeholder?: string
}

export function TagsInput({ value, onChange, placeholder = "Add tags..." }: TagsInputProps) {
  const tags = useMemo(() => value || [], [value])
  const [draft, setDraft] = useState("")

  const addTag = (tag: string) => {
    const cleaned = tag.trim()
    if (!cleaned || tags.includes(cleaned)) return
    onChange?.([...tags, cleaned])
    setDraft("")
  }

  const removeTag = (tag: string) => {
    onChange?.(tags.filter((t) => t !== tag))
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      addTag(draft)
    } else if (e.key === "Backspace" && !draft && tags.length) {
      removeTag(tags[tags.length - 1])
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <Badge key={tag} variant="secondary" className="text-xs flex items-center gap-1">
            {tag}
            <button
              type="button"
              className="text-[10px] opacity-70 hover:opacity-100"
              onClick={() => removeTag(tag)}
            >
              ✕
            </button>
          </Badge>
        ))}
      </div>
      <Input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => addTag(draft)}
        placeholder={placeholder}
      />
    </div>
  )
}

