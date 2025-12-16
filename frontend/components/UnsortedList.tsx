"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { UnsortedTaskCard } from "./UnsortedTaskCard";
import { API_BASE } from "@/lib/api";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function UnsortedList() {
  const { data, isLoading, error } = useSWR(
    `${API_BASE}/api/tasks/unsorted?user_id=1`,
    fetcher,
    { refreshInterval: 5000 } // Auto-refresh every 5 seconds
  );

  const [analyzing, setAnalyzing] = useState(false);

  const tasks = data?.tasks || [];

  const handleAnalyze = async (taskId: number) => {
    try {
      // Trigger LLM analysis for the task
      const response = await fetch(`${API_BASE}/api/tasks/${taskId}/analyze`, {
        method: "POST",
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Analysis failed:", errorText);
        toast.error("Failed to analyze task");
        return;
      }

      // Refresh the unsorted list
      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`);
      toast.success("Task analyzed successfully");
    } catch (error) {
      console.error("Analysis failed:", error);
      toast.error("Failed to analyze task");
    }
  };

  const handleSort = async (taskId: number, quadrant: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/tasks/${taskId}/sort`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quadrant }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Sort failed:", errorText);
        toast.error("Failed to sort task");
        return;
      }

      // Refresh both unsorted list and main tasks list
      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`);
      mutate(`${API_BASE}/api/tasks?user_id=1`);
      toast.success(`Task moved to ${quadrant}`);
    } catch (error) {
      console.error("Sort failed:", error);
      toast.error("Failed to sort task");
    }
  };

  const handleAnalyzeAll = async () => {
    if (!tasks || tasks.length === 0) return;

    setAnalyzing(true);
    try {
      const taskIds = tasks.map((t: any) => t.id);

      // Use batch analyze endpoint
      const response = await fetch(`${API_BASE}/api/tasks/analyze/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_ids: taskIds }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Batch analysis failed:", errorText);
        toast.error("Failed to analyze tasks");
        return;
      }

      // Refresh the unsorted list
      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`);
      toast.success(`Analyzed ${taskIds.length} tasks`);
    } catch (error) {
      console.error("Batch analysis failed:", error);
      toast.error("Failed to analyze tasks");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleTaskUpdate = (updatedTask: any) => {
    // If task is completed or deleted or sorted, removed from unsorted list
    if (updatedTask.status === "completed" || updatedTask.status === "deleted" || updatedTask.is_sorted) {
      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`, (currentData: any) => ({
        ...currentData,
        tasks: currentData?.tasks?.filter((t: any) => t.id !== updatedTask.id) || []
      }), false)
    } else {
      // Update in place
      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`, (currentData: any) => ({
        ...currentData,
        tasks: currentData?.tasks?.map((t: any) => t.id === updatedTask.id ? updatedTask : t) || []
      }), false)
    }
  }

  const handleTaskDelete = (taskId: number) => {
    mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`, (currentData: any) => ({
      ...currentData,
      tasks: currentData?.tasks?.filter((t: any) => t.id !== taskId) || []
    }), false)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading unsorted tasks...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-destructive">
          Error loading tasks: {error.message}
        </div>
      </div>
    );
  }

  return (
    <div className="unsorted-container p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-foreground">
          Unsorted Tasks ({tasks.length})
        </h2>
        {tasks.length > 0 && (
          <button
            onClick={handleAnalyzeAll}
            disabled={analyzing}
            className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {analyzing ? "⏳ Analyzing..." : "⚡ Analyze All"}
          </button>
        )}
      </div>

      <div className="space-y-4">
        {tasks.length > 0 ? (
          <AnimatePresence mode="popLayout">
            {tasks.map((task: any) => (
              <motion.div
                key={task.id}
                layout
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, x: -100, transition: { duration: 0.2 } }}
              >
                <UnsortedTaskCard
                  task={task}
                  onSort={handleSort}
                  onAnalyze={handleAnalyze}
                  onUpdate={handleTaskUpdate}
                  onDelete={handleTaskDelete}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        ) : (
          <div className="text-muted-foreground text-center py-8 bg-card rounded-lg border border-border shadow-sm">
            No unsorted tasks. All tasks are organized!
          </div>
        )}
      </div>
    </div>
  );
}
