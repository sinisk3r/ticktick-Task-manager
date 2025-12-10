"use client";

import { LLMSettings } from "@/components/LLMSettings";

export default function SettingsPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                <p className="text-muted-foreground mt-2">
                    Configure AI provider and application preferences.
                </p>
            </div>
            <div className="max-w-2xl">
                <LLMSettings />
            </div>
        </div>
    );
}
