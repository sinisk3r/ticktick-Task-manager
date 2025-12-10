"use client";

import { TaskAnalyzer } from "@/components/TaskAnalyzer";

export default function AnalyzePage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Analyze Task</h1>
                <p className="text-muted-foreground mt-2">
                    Use AI to break down your tasks and determine priority.
                </p>
            </div>
            <TaskAnalyzer />
        </div>
    );
}
