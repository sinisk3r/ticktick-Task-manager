"use client";

import { LLMSettings } from "@/components/LLMSettings";
import { ThemeToggle } from "@/components/theme-toggle";

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

            <div className="max-w-2xl">
                <h2 className="text-xl font-semibold mb-4">Appearance</h2>
                <div className="flex items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                        <label className="text-base font-medium">Theme</label>
                        <p className="text-sm text-muted-foreground">
                            Select the theme for the application.
                        </p>
                    </div>
                    <ThemeToggle />
                </div>
            </div>
        </div>
    );
}
