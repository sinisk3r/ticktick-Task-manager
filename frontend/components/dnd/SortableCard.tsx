"use client"

import { ReactNode } from "react"
import { UniqueIdentifier } from "@dnd-kit/core"
import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { cn } from "@/lib/utils"

type SortableCardProps = {
  id: UniqueIdentifier
  data?: Record<string, unknown>
  className?: string
  draggingClassName?: string
  children: (options: { isDragging: boolean }) => ReactNode
}

/**
 * Reusable sortable wrapper that applies dnd-kit transforms/animations
 * and forwards drag attributes/listeners to children via render props.
 */
export function SortableCard({
  id,
  data,
  className,
  draggingClassName,
  children,
}: SortableCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, data })

  const style = {
    transform: CSS.Translate.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "touch-none",
        className,
        isDragging ? draggingClassName || "opacity-30" : ""
      )}
      {...attributes}
      {...listeners}
    >
      {children({ isDragging })}
    </div>
  )
}


