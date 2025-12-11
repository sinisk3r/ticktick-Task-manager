"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { X, Send, Loader2, Sparkles, Square, RotateCcw, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ChatMessage, useChatStream } from "@/lib/useChatStream";

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
}: {
    message: ChatMessage;
    showThinking?: boolean;
    thinking?: string;
    isStreaming: boolean;
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
                        {showThinking && thinking ? (
                            <div className="rounded-md border border-border/60 bg-muted/50 text-muted-foreground px-3 py-2 shadow-sm">
                                <button
                                    type="button"
                                    className="flex items-center gap-2 text-[11px] uppercase tracking-wide"
                                    onClick={() => setCollapsed((v) => !v)}
                                >
                                    {isStreaming && !collapsed ? (
                                        <Loader2 className="size-3 animate-spin" />
                                    ) : (
                                        <Check className="size-3 text-foreground/70" />
                                    )}
                                    <span>Thinking…</span>
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
                        <div
                            className="prose prose-invert prose-p:my-0 prose-ul:my-1 prose-li:my-0 prose-li:marker:text-muted-foreground/80 text-sm"
                            dangerouslySetInnerHTML={{
                                __html: renderMarkdownLite(message.content || "Thinking…"),
                            }}
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
    const { messages, isStreaming, error, thinking, sendMessage, stop, clear } = useChatStream();
    const [input, setInput] = useState("");
    const scrollRef = useRef<HTMLDivElement | null>(null);

    const placeholder = useMemo(
        () => "Ask to plan your day, draft replies, or triage tasks…",
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
        await sendMessage(toSend, { context });
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
                            <li>“Draft a response to the budget email.”</li>
                            <li>“Which Q1 tasks can I finish in 30 minutes?”</li>
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
                                    showThinking={thinking && isLastAssistant}
                                    thinking={thinking && isLastAssistant ? thinking : undefined}
                                    isStreaming={isStreaming}
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
                                }}
                                showThinking
                                thinking={thinking}
                                isStreaming={isStreaming}
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
                            Streaming via `/api/chat/stream`
                        </p>
                    </div>
                </div>
            </footer>
        </aside>
    );
}

