"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Code2, FlaskConical } from "lucide-react";

export function DeveloperSettings() {
    const [devMode, setDevMode] = useState(false);

    useEffect(() => {
        // Load dev mode from localStorage
        const stored = localStorage.getItem("dev_mode");
        setDevMode(stored === "true");
    }, []);

    const handleToggle = (checked: boolean) => {
        setDevMode(checked);
        localStorage.setItem("dev_mode", String(checked));

        // Dispatch custom event so other components can react
        window.dispatchEvent(new CustomEvent("dev-mode-changed", { detail: { enabled: checked } }));
    };

    return (
        <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
                <Code2 className="size-5" />
                <h2 className="text-xl font-semibold">Developer Settings</h2>
                <Badge variant="secondary" className="ml-auto">
                    <FlaskConical className="size-3 mr-1" />
                    Experimental
                </Badge>
            </div>

            <div className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                        <label className="text-base font-medium">Developer Mode</label>
                        <p className="text-sm text-muted-foreground">
                            Enable debugging features like chat export, API inspection, and detailed event logging.
                        </p>
                    </div>
                    <Switch checked={devMode} onCheckedChange={handleToggle} />
                </div>

                {devMode && (
                    <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 p-4">
                        <p className="text-sm text-amber-600 dark:text-amber-400 font-medium">
                            Developer mode enabled
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            You now have access to debugging tools in the chat panel, including chat log export with full event traces.
                        </p>
                    </div>
                )}
            </div>
        </Card>
    );
}
