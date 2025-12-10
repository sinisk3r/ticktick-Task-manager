"use client";

import { TaskList } from "@/components/TaskList";

export default function TasksPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">My Tasks</h1>
                <p className="text-muted-foreground mt-2">
                    Manage and organize your prioritized tasks.
                </p>
            </div>
            <TaskList />
        </div>
    );
}
