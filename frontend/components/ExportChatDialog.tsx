"use client";

import { useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Download, FileText, FileJson, Loader2, Clipboard, Check } from "lucide-react";
import { AgentMessage } from "@/lib/useAgentStream";

interface ExportOptions {
    includeEvents: boolean;
    includeMetadata: boolean;
    includeApiContext: boolean;
    includeDurations: boolean;
    includeBrowserInfo: boolean;
    format: "markdown" | "json" | "both";
    condensedMode: boolean;
    maxPayloadSize: number;
}

interface ExportChatDialogProps {
    isOpen: boolean;
    onClose: () => void;
    messages: AgentMessage[];
}

export function ExportChatDialog({ isOpen, onClose, messages }: ExportChatDialogProps) {
    const [options, setOptions] = useState<ExportOptions>({
        includeEvents: true,
        includeMetadata: true,
        includeApiContext: true,
        includeDurations: true,
        includeBrowserInfo: true,
        format: "markdown",
        condensedMode: false,
        maxPayloadSize: 2000,
    });
    const [exporting, setExporting] = useState(false);
    const [copied, setCopied] = useState(false);

    const toggleOption = (key: keyof Omit<ExportOptions, "format" | "maxPayloadSize">) => {
        setOptions((prev) => ({ ...prev, [key]: !prev[key] }));
    };

    const getApiUrl = () => {
        if (typeof window === "undefined") return "N/A";
        return localStorage.getItem("backend_url") || process.env.NEXT_PUBLIC_API_URL || "http://localhost:5405";
    };

    const getBrowserInfo = () => {
        if (typeof window === "undefined") return {};
        return {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            screenResolution: `${window.screen.width}x${window.screen.height}`,
            viewportSize: `${window.innerWidth}x${window.innerHeight}`,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        };
    };

    const formatDuration = (ms: number) => {
        if (ms < 1000) return `${ms}ms`;
        if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
        return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
    };

    // Summarize tool results for condensed mode
    const summarizeToolResult = (result: unknown): string => {
        if (!result) return "No result";
        if (typeof result === "string") {
            try {
                const parsed = JSON.parse(result);
                return summarizeToolResult(parsed);
            } catch {
                return result.length > 100 ? result.slice(0, 100) + "..." : result;
            }
        }
        if (typeof result !== "object") return String(result);
        const r = result as Record<string, unknown>;
        if (r.summary && typeof r.summary === "string") return r.summary;
        if (r.tasks && Array.isArray(r.tasks)) return `${r.tasks.length} task(s) returned`;
        if (r.task && typeof r.task === "object") {
            const task = r.task as Record<string, unknown>;
            return `Task: ${task.title || task.id}`;
        }
        if (r.error) return `Error: ${r.error}`;
        return "Result available";
    };

    // Truncate large payloads
    const truncatePayload = (payload: unknown, maxSize: number): string => {
        const str = JSON.stringify(payload, null, 2);
        if (str.length <= maxSize) return str;
        return str.slice(0, maxSize) + `\n... [Truncated ${str.length - maxSize} chars]`;
    };

    const generateMarkdown = () => {
        const lines: string[] = [];
        const exportTime = new Date().toISOString();

        // Header
        lines.push("# Chat Log Export");
        lines.push("");
        lines.push(`**Exported:** ${new Date(exportTime).toLocaleString()}`);
        lines.push(`**Total Messages:** ${messages.length}`);
        lines.push("");

        // API Context
        if (options.includeApiContext) {
            lines.push("## API Context");
            lines.push("");
            lines.push(`- **Backend URL:** ${getApiUrl()}`);
            lines.push(`- **Endpoint:** POST /api/agent/stream`);
            lines.push("");
        }

        // Browser Info
        if (options.includeBrowserInfo) {
            const browserInfo = getBrowserInfo();
            lines.push("## Browser Environment");
            lines.push("");
            lines.push(`- **User Agent:** ${browserInfo.userAgent}`);
            lines.push(`- **Platform:** ${browserInfo.platform}`);
            lines.push(`- **Language:** ${browserInfo.language}`);
            lines.push(`- **Screen:** ${browserInfo.screenResolution}`);
            lines.push(`- **Viewport:** ${browserInfo.viewportSize}`);
            lines.push(`- **Timezone:** ${browserInfo.timezone}`);
            lines.push("");
        }

        // Conversation
        lines.push("## Conversation");
        lines.push("");

        messages.forEach((msg, idx) => {
            const timestamp = new Date(msg.createdAt).toLocaleString();
            const role = msg.role === "user" ? "User" : "Assistant";

            lines.push(`### Message ${idx + 1}: ${role}`);
            lines.push("");

            if (options.includeMetadata) {
                lines.push(`- **ID:** \`${msg.id}\``);
                lines.push(`- **Timestamp:** ${timestamp}`);
                lines.push(`- **Role:** ${msg.role}`);

                if (idx > 0) {
                    const prevMsg = messages[idx - 1];
                    const duration = msg.createdAt - prevMsg.createdAt;
                    if (options.includeDurations) {
                        lines.push(`- **Time since previous:** ${formatDuration(duration)}`);
                    }
                }

                lines.push("");
            }

            // Content
            lines.push("**Content:**");
            lines.push("");
            lines.push(msg.content || "_No content_");
            lines.push("");

            // Events
            if (options.includeEvents && msg.events && msg.events.length > 0) {
                lines.push("**Agent Events:**");
                lines.push("");

                msg.events.forEach((event) => {
                    const eventTime = new Date(event.createdAt).toLocaleString();
                    lines.push(`- **${event.type}** (${eventTime})`);

                    if (event.data) {
                        const summary = event.data.summary || event.data.text || event.data.message || "";
                        if (summary) {
                            lines.push(`  - ${summary}`);
                        }

                        if (event.type === "tool_request" && event.data.tool) {
                            lines.push(`  - Tool: \`${event.data.tool}\``);
                            if (event.data.args) {
                                lines.push(`  - Args: \`${JSON.stringify(event.data.args)}\``);
                            }
                        }

                        if (event.type === "tool_result" && event.data.result) {
                            if (options.condensedMode) {
                                // Condensed: show summary only
                                lines.push(`  - Result: ${summarizeToolResult(event.data.result)}`);
                            } else {
                                // Full: show truncated result
                                const resultStr = typeof event.data.result === "string"
                                    ? event.data.result
                                    : truncatePayload(event.data.result, options.maxPayloadSize);
                                lines.push(`  - Result: ${resultStr}`);
                            }
                        }

                        if (event.type === "error" && event.data.error) {
                            lines.push(`  - Error: ${event.data.error}`);
                        }
                    }
                });

                lines.push("");
            }

            // Payload
            if (options.includeMetadata && msg.payload && Object.keys(msg.payload).length > 0) {
                lines.push("**Payload:**");
                lines.push("");
                lines.push("```json");
                lines.push(JSON.stringify(msg.payload, null, 2));
                lines.push("```");
                lines.push("");
            }

            lines.push("---");
            lines.push("");
        });

        return lines.join("\n");
    };

    const generateJSON = () => {
        const exportData = {
            exportedAt: new Date().toISOString(),
            totalMessages: messages.length,
            apiContext: options.includeApiContext ? {
                backendUrl: getApiUrl(),
                endpoint: "POST /api/agent/stream",
            } : undefined,
            browserInfo: options.includeBrowserInfo ? getBrowserInfo() : undefined,
            messages: messages.map((msg, idx) => ({
                index: idx + 1,
                id: options.includeMetadata ? msg.id : undefined,
                role: msg.role,
                content: msg.content,
                timestamp: new Date(msg.createdAt).toISOString(),
                timestampMs: msg.createdAt,
                timeSincePrevious: options.includeDurations && idx > 0
                    ? msg.createdAt - messages[idx - 1].createdAt
                    : undefined,
                events: options.includeEvents ? msg.events : undefined,
                payload: options.includeMetadata ? msg.payload : undefined,
            })),
        };

        return JSON.stringify(exportData, null, 2);
    };

    const handleCopyToClipboard = async () => {
        setExporting(true);
        setCopied(false);

        try {
            let textToCopy = "";

            if (options.format === "markdown") {
                textToCopy = generateMarkdown();
            } else if (options.format === "json") {
                textToCopy = generateJSON();
            } else if (options.format === "both") {
                // For "both", copy markdown with JSON appended
                textToCopy = generateMarkdown() + "\n\n---\n\n# JSON Export\n\n```json\n" + generateJSON() + "\n```";
            }

            await navigator.clipboard.writeText(textToCopy);
            setCopied(true);

            setTimeout(() => {
                setExporting(false);
                setCopied(false);
                onClose();
            }, 1500);
        } catch (error) {
            console.error("Copy to clipboard failed:", error);
            setExporting(false);
        }
    };

    const handleExport = async () => {
        setExporting(true);

        try {
            if (options.format === "markdown" || options.format === "both") {
                const markdown = generateMarkdown();
                const blob = new Blob([markdown], { type: "text/markdown" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `chat-export-${Date.now()}.md`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }

            if (options.format === "json" || options.format === "both") {
                const json = generateJSON();
                const blob = new Blob([json], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `chat-export-${Date.now()}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }

            setTimeout(() => {
                setExporting(false);
                onClose();
            }, 500);
        } catch (error) {
            console.error("Export failed:", error);
            setExporting(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Export Chat Log</DialogTitle>
                    <DialogDescription>
                        Configure what information to include in the export. This is optimized for LLM analysis and debugging.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-3">
                        <h3 className="text-sm font-medium">Export Format</h3>
                        <div className="flex gap-2">
                            <Button
                                variant={options.format === "markdown" ? "default" : "outline"}
                                size="sm"
                                onClick={() => setOptions({ ...options, format: "markdown" })}
                                className="flex-1"
                            >
                                <FileText className="size-4 mr-2" />
                                Markdown
                            </Button>
                            <Button
                                variant={options.format === "json" ? "default" : "outline"}
                                size="sm"
                                onClick={() => setOptions({ ...options, format: "json" })}
                                className="flex-1"
                            >
                                <FileJson className="size-4 mr-2" />
                                JSON
                            </Button>
                            <Button
                                variant={options.format === "both" ? "default" : "outline"}
                                size="sm"
                                onClick={() => setOptions({ ...options, format: "both" })}
                                className="flex-1"
                            >
                                Both
                            </Button>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <h3 className="text-sm font-medium">Include in Export</h3>
                        <div className="space-y-2">
                            <label className="flex items-start gap-3 cursor-pointer">
                                <Checkbox
                                    checked={options.includeEvents}
                                    onCheckedChange={() => toggleOption("includeEvents")}
                                />
                                <div className="flex-1">
                                    <div className="text-sm font-medium">Agent Events</div>
                                    <div className="text-xs text-muted-foreground">
                                        Tool calls, thinking steps, and execution results
                                    </div>
                                </div>
                            </label>

                            <label className="flex items-start gap-3 cursor-pointer">
                                <Checkbox
                                    checked={options.includeMetadata}
                                    onCheckedChange={() => toggleOption("includeMetadata")}
                                />
                                <div className="flex-1">
                                    <div className="text-sm font-medium">Metadata</div>
                                    <div className="text-xs text-muted-foreground">
                                        Message IDs, payloads, and trace information
                                    </div>
                                </div>
                            </label>

                            <label className="flex items-start gap-3 cursor-pointer">
                                <Checkbox
                                    checked={options.includeApiContext}
                                    onCheckedChange={() => toggleOption("includeApiContext")}
                                />
                                <div className="flex-1">
                                    <div className="text-sm font-medium">API Context</div>
                                    <div className="text-xs text-muted-foreground">
                                        Backend URL and endpoint information
                                    </div>
                                </div>
                            </label>

                            <label className="flex items-start gap-3 cursor-pointer">
                                <Checkbox
                                    checked={options.includeDurations}
                                    onCheckedChange={() => toggleOption("includeDurations")}
                                />
                                <div className="flex-1">
                                    <div className="text-sm font-medium">Timing Data</div>
                                    <div className="text-xs text-muted-foreground">
                                        Response times and durations between messages
                                    </div>
                                </div>
                            </label>

                            <label className="flex items-start gap-3 cursor-pointer">
                                <Checkbox
                                    checked={options.includeBrowserInfo}
                                    onCheckedChange={() => toggleOption("includeBrowserInfo")}
                                />
                                <div className="flex-1">
                                    <div className="text-sm font-medium">Browser Environment</div>
                                    <div className="text-xs text-muted-foreground">
                                        User agent, platform, screen size, timezone
                                    </div>
                                </div>
                            </label>

                            <label className="flex items-start gap-3 cursor-pointer">
                                <Checkbox
                                    checked={options.condensedMode}
                                    onCheckedChange={() => toggleOption("condensedMode")}
                                />
                                <div className="flex-1">
                                    <div className="text-sm font-medium flex items-center gap-2">
                                        Condensed Mode
                                        <Badge variant="secondary" className="text-[10px]">Debug</Badge>
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        Summarize tool results instead of full JSON payloads
                                    </div>
                                </div>
                            </label>
                        </div>
                    </div>

                    <div className="rounded-lg border border-blue-500/50 bg-blue-500/10 p-3">
                        <p className="text-xs text-blue-600 dark:text-blue-400">
                            <strong>LLM Analysis Optimized:</strong> The export format is designed to be easily analyzed by LLMs like Claude,
                            with clear structure, timestamps, and event traces for debugging conversations.
                        </p>
                    </div>
                </div>

                <DialogFooter className="flex-row gap-2">
                    <Button variant="outline" onClick={onClose} disabled={exporting} className="flex-1">
                        Cancel
                    </Button>
                    <Button
                        variant="outline"
                        onClick={handleCopyToClipboard}
                        disabled={exporting || messages.length === 0}
                        className="flex-1"
                    >
                        {copied ? (
                            <>
                                <Check className="size-4 mr-2 text-green-500" />
                                Copied!
                            </>
                        ) : exporting ? (
                            <>
                                <Loader2 className="size-4 mr-2 animate-spin" />
                                Copying...
                            </>
                        ) : (
                            <>
                                <Clipboard className="size-4 mr-2" />
                                Copy
                            </>
                        )}
                    </Button>
                    <Button onClick={handleExport} disabled={exporting || messages.length === 0} className="flex-1">
                        {exporting && !copied ? (
                            <>
                                <Loader2 className="size-4 mr-2 animate-spin" />
                                Exporting...
                            </>
                        ) : (
                            <>
                                <Download className="size-4 mr-2" />
                                Download
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
