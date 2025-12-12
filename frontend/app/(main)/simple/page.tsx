"use client";

import { useState } from "react";
import { mutate } from "swr";
import { UnsortedList } from "@/components/UnsortedList";
import { API_BASE } from "@/lib/api";

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
      <h1 className="text-3xl font-bold mb-6 text-foreground">Simple Task View</h1>

      <div className="bg-card rounded-lg p-6 mb-8 border border-border shadow-sm">
        <h2 className="text-xl font-semibold mb-4 text-card-foreground">
          Quick Add Task
        </h2>
        <input
          type="text"
          placeholder="Task title..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyPress={handleKeyPress}
          className="w-full px-4 py-2 bg-input text-foreground rounded mb-3 border border-border focus:border-ring focus:outline-none placeholder:text-muted-foreground"
        />
        <textarea
          placeholder="Description (optional)..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="w-full px-4 py-2 bg-input text-foreground rounded mb-3 border border-border focus:border-ring focus:outline-none resize-none placeholder:text-muted-foreground"
        />
        <button
          onClick={handleCreateTask}
          disabled={creating || !title.trim()}
          className="w-full px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {creating ? "⏳ Creating..." : "Add Task (syncs to TickTick)"}
        </button>
      </div>

      <UnsortedList />
    </div>
  );
}
