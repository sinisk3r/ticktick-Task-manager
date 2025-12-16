"use client"

import { cn } from "@/lib/utils"

interface DescriptionPreviewProps {
    markdown: string
    maxLines?: number
    className?: string
}

export function DescriptionPreview({
    markdown,
    maxLines = 3,
    className
}: DescriptionPreviewProps) {
    if (!markdown || markdown.trim() === "") {
        return null
    }

    // Split by lines and take first maxLines
    const lines = markdown.split("\n").slice(0, maxLines)

    const renderLine = (line: string, index: number) => {
        // Check for checkbox pattern: - [ ] or - [x]
        const checkboxMatch = line.match(/^[-*]\s*\[([ xX])\]\s*(.+)/)

        if (checkboxMatch) {
            const [, checked, text] = checkboxMatch
            const isChecked = checked.toLowerCase() === "x"

            return (
                <div key={index} className="flex items-start gap-2">
                    <input
                        type="checkbox"
                        checked={isChecked}
                        disabled
                        className="mt-0.5 cursor-default"
                    />
                    <span className={cn(
                        "text-sm",
                        isChecked && "line-through opacity-60"
                    )}>
                        {text.trim()}
                    </span>
                </div>
            )
        }

        // Regular line - strip markdown formatting for preview
        let cleanLine = line
            // Remove bold/italic
            .replace(/\*\*(.+?)\*\*/g, "$1")
            .replace(/\*(.+?)\*/g, "$1")
            .replace(/__(.+?)__/g, "$1")
            .replace(/_(.+?)_/g, "$1")
            // Remove links but keep text
            .replace(/\[(.+?)\]\(.+?\)/g, "$1")
            // Remove headers
            .replace(/^#{1,6}\s+/, "")
            // Remove inline code
            .replace(/`(.+?)`/g, "$1")
            .trim()

        if (!cleanLine) return null

        return (
            <p key={index} className="text-sm text-muted-foreground line-clamp-1">
                {cleanLine}
            </p>
        )
    }

    const hasMore = markdown.split("\n").length > maxLines

    return (
        <div className={cn("space-y-1", className)}>
            {lines.map((line, i) => renderLine(line, i))}
            {hasMore && (
                <span className="text-xs text-muted-foreground italic">
                    ...
                </span>
            )}
        </div>
    )
}
