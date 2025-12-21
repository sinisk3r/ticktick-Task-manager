"use client";

import { CheckCircle2, Folder } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TaskDetailPopover } from "@/components/TaskDetailPopover";
import { Task } from "@/types/task";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";

interface ChatTaskCardProps {
  task: Task;
  onUpdate?: (task: Task) => void;
  onDelete?: (taskId: number) => void;
  onToggleStatus?: (task: Task) => void;
}

const getQuadrantColor = (quadrant?: string) => {
  const colors = {
    Q1: "border-l-red-500",
    Q2: "border-l-green-500",
    Q3: "border-l-yellow-500",
    Q4: "border-l-blue-500",
  };
  return colors[quadrant as keyof typeof colors] || "border-l-gray-500";
};

export function ChatTaskCard({ task, onUpdate, onDelete, onToggleStatus }: ChatTaskCardProps) {
  const effectiveQuadrant =
    task.manual_quadrant_override || task.effective_quadrant || task.eisenhower_quadrant || "Q4";
  const isCompleted = task.status === "completed";

  // Truncate title for compact display
  const displayTitle = task.title.length > 60 ? task.title.substring(0, 57) + "..." : task.title;

  return (
    <TaskDetailPopover
      task={task}
      onUpdate={onUpdate}
      onDelete={onDelete}
      trigger={
        <Card
          className={cn(
            "p-3 border-l-4 transition-all hover:shadow-md cursor-pointer",
            getQuadrantColor(effectiveQuadrant),
            isCompleted && "opacity-70"
          )}
        >
          <div className="flex items-start gap-2">
            <Button
              variant={isCompleted ? "secondary" : "ghost"}
              size="icon"
              className="h-5 w-5 shrink-0 mt-0.5"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onToggleStatus?.(task);
              }}
            >
              <CheckCircle2
                className={cn(
                  "h-3.5 w-3.5",
                  isCompleted ? "text-primary" : "text-muted-foreground"
                )}
              />
            </Button>
            <div className="flex-1 min-w-0">
              <div className="flex items-start gap-2">
                <p
                  className={cn(
                    "text-sm font-medium flex-1",
                    isCompleted && "text-muted-foreground line-through"
                  )}
                >
                  {displayTitle}
                </p>
              </div>
              {task.project_name && (
                <div className="flex items-center gap-1 mt-1.5">
                  <Folder className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">{task.project_name}</span>
                </div>
              )}
            </div>
          </div>
        </Card>
      }
    />
  );
}

