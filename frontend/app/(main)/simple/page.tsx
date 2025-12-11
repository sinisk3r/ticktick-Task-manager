"use client";

import { useState } from "react";
import { mutate } from "swr";
import { UnsortedList } from "@/components/UnsortedList";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SimpleTaskView() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreateTask = async () => {
    if (!title.trim()) return;

    setCreating(true);
    try {
      const response = await fetch(`${API_BASE}/api/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description,
          user_id: 1, // TODO: Get from auth context
        }),
      });

      if (response.ok) {
        setTitle("");
        setDescription("");
        // Refresh unsorted list
        mutate(`${API_BASE}/api/tasks/unsorted?user_id=1`);
      } else {
        console.error("Failed to create task:", await response.text());
      }
    } catch (error) {
      console.error("Failed to create task:", error);
    } finally {
      setCreating(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleCreateTask();
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6 text-white">Simple Task View</h1>

      <div className="bg-gray-800 rounded-lg p-6 mb-8 border border-gray-700">
        <h2 className="text-xl font-semibold mb-4 text-white">
          Quick Add Task
        </h2>
        <input
          type="text"
          placeholder="Task title..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyPress={handleKeyPress}
          className="w-full px-4 py-2 bg-gray-700 text-white rounded mb-3 border border-gray-600 focus:border-blue-500 focus:outline-none"
        />
        <textarea
          placeholder="Description (optional)..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="w-full px-4 py-2 bg-gray-700 text-white rounded mb-3 border border-gray-600 focus:border-blue-500 focus:outline-none resize-none"
        />
        <button
          onClick={handleCreateTask}
          disabled={creating || !title.trim()}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {creating ? "⏳ Creating..." : "Add Task (syncs to TickTick)"}
        </button>
      </div>

      <UnsortedList />
    </div>
  );
}
