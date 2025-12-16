"use client";

import { useState } from "react";
import { QuadrantPicker } from "./QuadrantPicker";
import { TaskDetailPopover } from "./TaskDetailPopover";
import { DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api";
import { Task } from "@/types/task";

interface UnsortedTaskCardProps {
  task: Task;
  onSort: (taskId: number, quadrant: string) => void;
  onAnalyze: (taskId: number) => void;
  onUpdate?: (task: Task) => void;
  onDelete?: (taskId: number) => void;
}

export function UnsortedTaskCard({
  task,
  onSort,
  onAnalyze,
  onUpdate,
  onDelete,
}: UnsortedTaskCardProps) {
  const [showPicker, setShowPicker] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      // Call the analyze API endpoint
      const response = await fetch(`${API_BASE}/api/tasks/${task.id}/analyze`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      // Call parent handler to refresh task
      await onAnalyze(task.id);
    } catch (error) {
      console.error('Failed to analyze task:', error);
    } finally {
      setAnalyzing(false);
    }
  };

  const priorityLabel = (priority: number) => {
    const labels: { [key: number]: string } = {
      0: "None",
      1: "Low",
      3: "Medium",
      5: "High",
    };
    return labels[priority] || "None";
  };

  return (
    <div className="bg-card rounded-lg p-4 border border-border hover:border-primary/50 transition-colors">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <TaskDetailPopover
            task={task}
            onUpdate={onUpdate}
            onDelete={onDelete}
            trigger={
              <DialogTrigger asChild>
                <h3 className="text-lg font-semibold text-foreground mb-1 cursor-pointer hover:text-primary transition-colors">
                  {task.title}
                </h3>
              </DialogTrigger>
            }
          />
          {task.description && (
            <p className="text-muted-foreground text-sm mb-2 line-clamp-2">
              {task.description}
            </p>
          )}
          <div className="flex gap-2 flex-wrap">
            {(task.ticktick_priority ?? 0) > 0 && (
              <Badge variant="secondary" className="text-xs">
                Priority: {priorityLabel(task.ticktick_priority ?? 0)}
              </Badge>
            )}
            {task.project_name && (
              <Badge variant="outline" className="text-xs">
                {task.project_name}
              </Badge>
            )}
            {task.ticktick_tags && task.ticktick_tags.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {task.ticktick_tags.join(", ")}
              </Badge>
            )}
            {task.eisenhower_quadrant && (
              <Badge variant="default" className="text-xs">
                AI Suggests: {task.eisenhower_quadrant}
              </Badge>
            )}
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        <Button
          onClick={handleAnalyze}
          disabled={analyzing}
          size="sm"
          variant="default"
        >
          {analyzing ? "⏳ Analyzing..." : "⚡ Analyze"}
        </Button>

        <Button
          onClick={() => setShowPicker(true)}
          size="sm"
          variant="outline"
        >
          📊 Sort Manually
        </Button>
      </div>

      {showPicker && (
        <QuadrantPicker
          onSelect={(quadrant) => {
            onSort(task.id, quadrant);
            setShowPicker(false);
          }}
          onCancel={() => setShowPicker(false)}
        />
      )}
    </div>
  );
}
