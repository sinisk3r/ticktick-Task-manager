"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
    X,
    Send,
    Loader2,
    Sparkles,
    Square,
    RotateCcw,
    Check,
    Wand2,
    ClipboardList,
    Workflow,
    AlertTriangle,
    Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
    AgentEvent,
    AgentMessage,
    PendingAction,
    useAgentStream,
} from "@/lib/useAgentStream";
import { ExportChatDialog } from "@/components/ExportChatDialog";

const escapeHtml = (value: string) =>
    value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");

const renderMarkdownLite = (value: string) => {
    let html = escapeHtml(value);
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
    html = html.replace(/`(.+?)`/g, "<code>$1</code>");
    html = html.replace(/\n/g, "<br>");
    return html;
};

const EventRow = ({ event }: { event: AgentEvent }) => {
    const type = event.type;
    const data = event.data || {};

    // For message_chunk events, render as prose text
    if (type === "message_chunk" && event.text) {
        return null; // These will be accumulated and rendered separately
    }

    const summary =
        data.summary ||
        data.text ||
        data.delta ||
        data.message ||
        data.result?.summary ||
        data.result?.message ||
        data.result?.analysis?.reasoning ||
        "";

    const iconMap: Record<string, React.ReactNode> = {
        thinking: <Wand2 className="size-3.5 text-muted-foreground" />,
        step: <Workflow className="size-3.5 text-muted-foreground" />,
        tool_request: <ClipboardList className="size-3.5 text-muted-foreground" />,
        tool_result: <Check className="size-3.5 text-emerald-500" />,
        message: <Sparkles className="size-3.5 text-primary" />,
        message_chunk: <Sparkles className="size-3.5 text-primary" />,
        error: <AlertTriangle className="size-3.5 text-destructive" />,
        done: <Check className="size-3.5 text-muted-foreground" />,
    };

    return (
        <div className="flex items-start gap-2 text-xs leading-tight px-3 py-2 rounded-md border border-border/40 bg-muted/20">
            <span className="mt-0.5">{iconMap[type] || <Sparkles className="size-3.5" />}</span>
            <div className="flex-1">
                <div className="font-medium capitalize text-foreground/80">{type.replace("_", " ")}</div>
                {summary ? <p className="text-muted-foreground mt-0.5">{summary}</p> : null}
                {type === "tool_request" && data.tool ? (
                    <p className="text-[11px] text-muted-foreground/80 mt-0.5">Tool: {data.tool}</p>
                ) : null}
            </div>
        </div>
    );
};

// Render events chronologically, interleaving text chunks and tool actions
const renderChronologicalEvents = (events: AgentEvent[], fallbackContent: string, isStreaming: boolean) => {
    if (!events.length) {
        // No events yet - show animated thinking if streaming, otherwise show content
        if (!fallbackContent && isStreaming) {
            return (
                <div className="flex items-center gap-2">
                    <AnimatedThinkingText />
                </div>
            );
        }
        // Fall back to rendering content as-is
        return (
            <div
                className="prose prose-invert prose-p:my-0 prose-ul:my-1 prose-li:my-0 prose-li:marker:text-muted-foreground/80 text-sm"
                dangerouslySetInnerHTML={{
                    __html: renderMarkdownLite(fallbackContent || ""),
                }}
            />
        );
    }

    const segments: React.ReactNode[] = [];
    let currentTextBuffer = "";

    for (let i = 0; i < events.length; i++) {
        const event = events[i];

        if (event.type === "message_chunk" && event.text) {
            // Accumulate text chunks
            currentTextBuffer += event.text;
        } else if (event.type === "message" && event.data.message) {
            // Complete message (from tool summaries, etc.)
            currentTextBuffer += "\n" + event.data.message;
        } else {
            // Non-text event (tool call, step, etc.) - flush text buffer first, then render the event
            if (currentTextBuffer.trim()) {
                segments.push(
                    <div
                        key={`text-${i}`}
                        className="prose prose-invert prose-p:my-0 prose-ul:my-1 prose-li:my-0 prose-li:marker:text-muted-foreground/80 text-sm"
                        dangerouslySetInnerHTML={{
                            __html: renderMarkdownLite(currentTextBuffer.trim()),
                        }}
                    />
                );
                currentTextBuffer = "";
            }

            // Render tool events inline (chronologically)
            if (event.type === "tool_request" || event.type === "tool_result" || event.type === "step") {
                segments.push(
                    <div key={`event-${event.id}`} className="my-2">
                        <EventRow event={event} />
                    </div>
                );
            }
        }
    }

    // Flush remaining text
    if (currentTextBuffer.trim()) {
        segments.push(
            <div
                key="text-final"
                className="prose prose-invert prose-p:my-0 prose-ul:my-1 prose-li:my-0 prose-li:marker:text-muted-foreground/80 text-sm"
                dangerouslySetInnerHTML={{
                    __html: renderMarkdownLite(currentTextBuffer.trim()),
                }}
            />
        );
    }

    // If no segments, fall back to content or animated thinking
    if (segments.length === 0) {
        if (!fallbackContent && isStreaming) {
            return (
                <div className="flex items-center gap-2">
                    <AnimatedThinkingText />
                </div>
            );
        }
        return (
            <div
                className="prose prose-invert prose-p:my-0 prose-ul:my-1 prose-li:my-0 prose-li:marker:text-muted-foreground/80 text-sm"
                dangerouslySetInnerHTML={{
                    __html: renderMarkdownLite(fallbackContent || ""),
                }}
            />
        );
    }

    return <>{segments}</>;
};

const AgentTimeline = ({
    events,
    pendingAction,
    onConfirm,
    onCancel,
}: {
    events: AgentEvent[];
    pendingAction: PendingAction | null;
    onConfirm: () => void;
    onCancel: () => void;
}) => {
    // Only show for pending confirmations (events are now rendered chronologically inline)
    if (!pendingAction) return null;

    return (
        <div className="mt-2 rounded-md border border-border/60 bg-muted/40">
            <div className="divide-y divide-border/60 px-3 py-2">
                <div className="flex items-center gap-2 text-xs">
                    <AlertTriangle className="size-3.5 text-amber-500" />
                    <span className="flex-1 text-muted-foreground">
                        {pendingAction.tool} needs confirmation.
                    </span>
                    <Button size="sm" variant="destructive" onClick={onConfirm}>
                        Confirm
                    </Button>
                    <Button size="sm" variant="ghost" onClick={onCancel}>
                        Cancel
                    </Button>
                </div>
            </div>
        </div>
    );
};

// Animated thinking text component that cycles through creative words with typing effect
const AnimatedThinkingText = () => {
    const words = ["Planning", "Thinking", "Doodling", "Musing", "Dreaming", "Scribbling", "Sketching"];
    // Randomize starting word index so it doesn't always start with "Planning"
    const [currentWordIndex, setCurrentWordIndex] = useState(() => Math.floor(Math.random() * words.length));
    const [displayText, setDisplayText] = useState("");
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        const currentWord = words[currentWordIndex];
        const typingSpeed = isDeleting ? 50 : 100; // Faster when deleting
        const pauseAfterTyping = 2000; // Pause before starting to delete
        const pauseAfterDeleting = 200; // Brief pause before next word

        let timeout: NodeJS.Timeout;

        if (!isDeleting && displayText === currentWord) {
            // Finished typing, pause before deleting
            timeout = setTimeout(() => setIsDeleting(true), pauseAfterTyping);
        } else if (isDeleting && displayText === "") {
            // Finished deleting, move to next word
            timeout = setTimeout(() => {
                setIsDeleting(false);
                setCurrentWordIndex((prev) => (prev + 1) % words.length);
            }, pauseAfterDeleting);
        } else if (!isDeleting) {
            // Typing character by character
            timeout = setTimeout(() => {
                setDisplayText(currentWord.substring(0, displayText.length + 1));
            }, typingSpeed);
        } else {
            // Deleting character by character
            timeout = setTimeout(() => {
                setDisplayText(currentWord.substring(0, displayText.length - 1));
            }, typingSpeed);
        }

        return () => clearTimeout(timeout);
    }, [displayText, isDeleting, currentWordIndex]);

    return (
        <>
            <span className="animate-shake inline-block text-base">✏️</span>
            <span className="text-muted-foreground">{displayText}...</span>
        </>
    );
};

interface ChatPanelProps {
    isOpen: boolean;
    onClose: () => void;
    isMobile?: boolean;
    context?: Record<string, unknown>;
}

const MessageBubble = ({
    message,
    showThinking,
    thinking,
    isStreaming,
    pendingAction,
    onConfirm,
    onCancel,
}: {
    message: AgentMessage;
    showThinking?: boolean;
    thinking?: string;
    isStreaming: boolean;
    pendingAction: PendingAction | null;
    onConfirm: () => void;
    onCancel: () => void;
}) => {
    const isAssistant = message.role === "assistant";
    const [collapsed, setCollapsed] = useState(false);

    // Auto-collapse once streaming completes
    useEffect(() => {
        if (!isStreaming && showThinking) {
            setCollapsed(true);
        }
    }, [isStreaming, showThinking]);

    return (
        <div className={cn("flex", isAssistant ? "items-start" : "justify-end")}>
            <div
                className={cn(
                    "rounded-lg px-3 py-2 text-sm shadow-sm",
                    isAssistant
                        ? "bg-muted text-foreground max-w-[90%]"
                        : "bg-primary text-primary-foreground max-w-[85%]",
                )}
            >
                {isAssistant ? (
                    <div className="space-y-2">
                        {showThinking && thinking && thinking.trim() ? (
                            <div className="rounded-md border border-border/60 bg-muted/50 text-muted-foreground px-3 py-2 shadow-sm">
                                <button
                                    type="button"
                                    className="flex items-center gap-2 text-[11px] uppercase tracking-wide"
                                    onClick={() => setCollapsed((v) => !v)}
                                >
                                    {isStreaming && !collapsed ? (
                                        <AnimatedThinkingText />
                                    ) : (
                                        <>
                                            <Check className="size-3 text-foreground/70" />
                                            <span className="text-muted-foreground">Thinking</span>
                                        </>
                                    )}
                                </button>
                                <div
                                    className={cn(
                                        "transition-[max-height,opacity] duration-200 ease-in-out overflow-hidden",
                                        collapsed ? "max-h-0 opacity-0" : "max-h-64 opacity-100",
                                    )}
                                >
                                    <div className="mt-2 whitespace-pre-wrap text-sm leading-snug">{thinking}</div>
                                </div>
                            </div>
                        ) : null}
                        {/* Render events chronologically, interleaving text and tool calls */}
                        {renderChronologicalEvents(message.events, message.content, isStreaming)}
                        <AgentTimeline
                            events={message.events}
                            pendingAction={pendingAction}
                            onConfirm={onConfirm}
                            onCancel={onCancel}
                        />
                    </div>
                ) : (
                    message.content
                )}
            </div>
        </div>
    );
};

export function ChatPanel({ isOpen, onClose, isMobile, context }: ChatPanelProps) {
    const {
        messages,
        isStreaming,
        error,
        thinking,
        pendingAction,
        sendGoal,
        stop,
        clear,
        executePending,
    } = useAgentStream();
    const [input, setInput] = useState("");
    const [devMode, setDevMode] = useState(false);
    const [showExportDialog, setShowExportDialog] = useState(false);
    const scrollRef = useRef<HTMLDivElement | null>(null);

    // Listen for dev mode changes
    useEffect(() => {
        const stored = localStorage.getItem("dev_mode");
        setDevMode(stored === "true");

        const handleDevModeChange = (e: CustomEvent) => {
            setDevMode(e.detail.enabled);
        };

        window.addEventListener("dev-mode-changed", handleDevModeChange as EventListener);
        return () => {
            window.removeEventListener("dev-mode-changed", handleDevModeChange as EventListener);
        };
    }, []);

    const placeholder = useMemo(
        () => "Ask to plan your day, triage tasks, or create/complete items…",
        [],
    );

    useEffect(() => {
        if (!scrollRef.current) return;
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages, isStreaming]);

    const handleSend = async () => {
        if (!input.trim()) return;
        const toSend = input;
        setInput("");
        await sendGoal(toSend, { context });
    };

    const panelClass = cn(
        "border-l bg-background/95 backdrop-blur flex flex-col h-full shadow-lg transition-all duration-200",
        isOpen ? "translate-x-0" : "translate-x-full",
        isMobile ? "fixed right-0 top-0 bottom-0 w-full max-w-xl z-40" : "w-full max-w-sm",
    );

    return (
        <aside className={panelClass} aria-hidden={!isOpen}>
            <header className="flex items-center gap-2 px-4 py-3 border-b">
                <div className="flex items-center gap-2">
                    <Sparkles className="size-4 text-primary" />
                    <div>
                        <p className="text-sm font-semibold leading-none">Assistant</p>
                        <p className="text-xs text-muted-foreground">Streaming responses</p>
                    </div>
                </div>

                <div className="ml-auto flex items-center gap-2">
                    {isStreaming ? (
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={stop}
                            className="text-amber-500 hover:text-amber-600"
                            title="Stop response"
                        >
                            <Square className="size-4" />
                        </Button>
                    ) : null}
                    {devMode && messages.length > 0 && (
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setShowExportDialog(true)}
                            title="Export chat log (Dev)"
                            className="text-blue-500 hover:text-blue-600"
                        >
                            <Download className="size-4" />
                        </Button>
                    )}
                    <Button variant="ghost" size="icon" onClick={clear} title="Clear conversation">
                        <RotateCcw className="size-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={onClose} title="Close chat">
                        <X className="size-4" />
                    </Button>
                </div>
            </header>

            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
                {messages.length === 0 ? (
                    <div className="text-sm text-muted-foreground bg-muted/30 border rounded-lg px-3 py-3">
                        <p className="font-medium text-foreground">How I can help</p>
                        <ul className="mt-2 space-y-1 list-disc list-inside">
                            <li>“Plan my afternoon with focus blocks.”</li>
                            <li>“Complete task 12 and draft a summary.”</li>
                            <li>“Delete task 7” (will ask to confirm)</li>
                        </ul>
                    </div>
                ) : (
                    <>
                        {messages.map((msg, idx) => {
                            const isLastAssistant =
                                msg.role === "assistant" &&
                                messages.slice(idx + 1).findIndex((m) => m.role === "assistant") === -1;

                            return (
                                <MessageBubble
                                    key={msg.id}
                                    message={msg}
                                    showThinking={!!(thinking && isLastAssistant)}
                                    thinking={thinking && isLastAssistant ? thinking : undefined}
                                    isStreaming={isStreaming}
                                    pendingAction={isLastAssistant ? pendingAction : null}
                                    onConfirm={() => executePending("confirm")}
                                    onCancel={() => executePending("cancel")}
                                />
                            );
                        })}
                        {thinking && messages.every((m) => m.role !== "assistant") ? (
                            <MessageBubble
                                message={{
                                    id: "thinking-only",
                                    role: "assistant",
                                    content: "",
                                    createdAt: Date.now(),
                                    events: [],
                                }}
                                showThinking
                                thinking={thinking}
                                isStreaming={isStreaming}
                                pendingAction={null}
                                onConfirm={() => executePending("confirm")}
                                onCancel={() => executePending("cancel")}
                            />
                        ) : null}
                    </>
                )}
            </div>

            {error ? (
                <div className="px-4 py-2 text-sm text-destructive border-t border-b bg-destructive/10">
                    {error}
                </div>
            ) : null}

            <footer className="p-4 border-t">
                <div className="flex flex-col gap-2">
                    <Textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                handleSend();
                            }
                        }}
                        placeholder={placeholder}
                        className="min-h-[80px] resize-none"
                    />
                    <div className="flex items-center gap-2">
                        <Button
                            onClick={handleSend}
                            disabled={!input.trim()}
                            className="flex items-center gap-2"
                        >
                            {isStreaming ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                            Send
                        </Button>
                        <p className="text-xs text-muted-foreground ml-auto">
                            Streaming via `/api/agent/stream`
                        </p>
                    </div>
                </div>
            </footer>

            <ExportChatDialog
                isOpen={showExportDialog}
                onClose={() => setShowExportDialog(false)}
                messages={messages}
            />
        </aside>
    );
}

