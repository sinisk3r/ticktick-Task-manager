"use client"

import { ReactNode } from "react"

interface MetadataRowProps {
  icon: string
  label: string
  children: ReactNode
}

export function MetadataRow({ icon, label, children }: MetadataRowProps) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-lg">{icon}</span>
      <div className="flex-1">
        <label className="text-xs text-muted-foreground mb-1 block">{label}</label>
        {children}
      </div>
    </div>
  )
}
