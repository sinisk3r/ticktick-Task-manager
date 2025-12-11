"use client"

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"

interface QuadrantFilterProps {
  selectedQuadrant: string | null
  onQuadrantChange: (quadrant: string | null) => void
  taskCounts: {
    all: number
    Q1: number
    Q2: number
    Q3: number
    Q4: number
  }
}

export function QuadrantFilter({
  selectedQuadrant,
  onQuadrantChange,
  taskCounts,
}: QuadrantFilterProps) {
  return (
    <div className="mb-6">
      <Tabs
        value={selectedQuadrant || "all"}
        onValueChange={(value) =>
          onQuadrantChange(value === "all" ? null : value)
        }
        className="w-full"
      >
        <TabsList className="grid w-full grid-cols-5 h-auto">
          <TabsTrigger value="all" className="flex flex-col py-3 gap-1">
            <span className="text-sm font-medium">All Tasks</span>
            <Badge variant="secondary" className="text-xs">
              {taskCounts.all}
            </Badge>
          </TabsTrigger>

          <TabsTrigger value="Q1" className="flex flex-col py-3 gap-1">
            <span className="text-sm font-medium">🔴 Q1</span>
            <span className="text-xs text-muted-foreground">Urgent & Important</span>
            <Badge variant="destructive" className="text-xs">
              {taskCounts.Q1}
            </Badge>
          </TabsTrigger>

          <TabsTrigger value="Q2" className="flex flex-col py-3 gap-1">
            <span className="text-sm font-medium">🟢 Q2</span>
            <span className="text-xs text-muted-foreground">Not Urgent, Important</span>
            <Badge variant="default" className="text-xs bg-green-100 text-green-800 hover:bg-green-200 dark:bg-green-900 dark:text-green-100 dark:hover:bg-green-800">
              {taskCounts.Q2}
            </Badge>
          </TabsTrigger>

          <TabsTrigger value="Q3" className="flex flex-col py-3 gap-1">
            <span className="text-sm font-medium">🟡 Q3</span>
            <span className="text-xs text-muted-foreground">Urgent, Not Important</span>
            <Badge variant="secondary" className="text-xs bg-yellow-100 text-yellow-800 hover:bg-yellow-200 dark:bg-yellow-900 dark:text-yellow-100 dark:hover:bg-yellow-800">
              {taskCounts.Q3}
            </Badge>
          </TabsTrigger>

          <TabsTrigger value="Q4" className="flex flex-col py-3 gap-1">
            <span className="text-sm font-medium">🔵 Q4</span>
            <span className="text-xs text-gray-400">Neither</span>
            <Badge variant="outline" className="text-xs">
              {taskCounts.Q4}
            </Badge>
          </TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  )
}
