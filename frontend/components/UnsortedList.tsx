"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import { UnsortedTaskCard } from "./UnsortedTaskCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
        console.error("Analysis failed:", await response.text());
        return;
      }

      // Refresh the unsorted list
      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`);
    } catch (error) {
      console.error("Analysis failed:", error);
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
        console.error("Sort failed:", await response.text());
        return;
      }

      // Refresh both unsorted list and main tasks list
      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`);
      mutate(`${API_BASE}/api/tasks?user_id=1`);
    } catch (error) {
      console.error("Sort failed:", error);
    }
  };

  const handleAnalyzeAll = async () => {
    if (!tasks || tasks.length === 0) return;

    setAnalyzing(true);
    try {
      const taskIds = tasks.map((t: any) => t.id);

      // Analyze each task individually
      // TODO: Create batch analyze endpoint for efficiency
      for (const taskId of taskIds) {
        await handleAnalyze(taskId);
      }

      mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`);
    } catch (error) {
      console.error("Batch analysis failed:", error);
    } finally {
      setAnalyzing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-400">Loading unsorted tasks...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-red-400">
          Error loading tasks: {error.message}
        </div>
      </div>
    );
  }

  return (
    <div className="unsorted-container p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">
          Unsorted Tasks ({tasks.length})
        </h2>
        {tasks.length > 0 && (
          <button
            onClick={handleAnalyzeAll}
            disabled={analyzing}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {analyzing ? "⏳ Analyzing..." : "⚡ Analyze All"}
          </button>
        )}
      </div>

      <div className="space-y-4">
        {tasks.length > 0 ? (
          tasks.map((task: any) => (
            <UnsortedTaskCard
              key={task.id}
              task={task}
              onSort={handleSort}
              onAnalyze={handleAnalyze}
            />
          ))
        ) : (
          <div className="text-gray-500 text-center py-8 bg-gray-800 rounded-lg border border-gray-700">
            No unsorted tasks. All tasks are organized!
          </div>
        )}
      </div>
    </div>
  );
}
