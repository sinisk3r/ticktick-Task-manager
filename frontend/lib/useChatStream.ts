"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
    id: string;
    role: ChatRole;
    content: string;
    createdAt: number;
}

interface SendOptions {
    context?: Record<string, unknown>;
}

interface ParsedEvent {
    event: string;
    data: string;
}

const parseSSEChunk = (chunk: string): ParsedEvent | null => {
    const lines = chunk.split("\n").filter(Boolean);
    if (!lines.length) return null;

    let event = "message";
    let data = "";

    for (const line of lines) {
        if (line.startsWith("event:")) {
            event = line.replace("event:", "").trim();
        } else if (line.startsWith("data:")) {
            data += line.replace("data:", "").trim();
        }
    }

    return { event, data };
};

const newId = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);

export function useChatStream() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [thinking, setThinking] = useState("");

    const controllerRef = useRef<AbortController | null>(null);
    const assistantIdRef = useRef<string | null>(null);
    const messagesRef = useRef<ChatMessage[]>([]);

    useEffect(() => {
        messagesRef.current = messages;
    }, [messages]);

    const stop = useCallback(() => {
        controllerRef.current?.abort();
        setIsStreaming(false);
    }, []);

    const clear = useCallback(() => {
        setMessages([]);
        setError(null);
        setThinking("");
    }, []);

    const appendAssistantDelta = useCallback((delta: string) => {
        if (!assistantIdRef.current) return;
        setMessages((prev) =>
            prev.map((msg) =>
                msg.id === assistantIdRef.current
                    ? { ...msg, content: msg.content + delta }
                    : msg,
            ),
        );
    }, []);

    const sendMessage = useCallback(
        async (content: string, options?: SendOptions) => {
            const trimmed = content.trim();
            if (!trimmed) return;

            const userMessage: ChatMessage = {
                id: newId(),
                role: "user",
                content: trimmed,
                createdAt: Date.now(),
            };

            const assistantId = newId();
            assistantIdRef.current = assistantId;

            const history = [...messagesRef.current, userMessage].map((m) => ({
                role: m.role,
                content: m.content,
            }));

            setMessages((prev) => [
                ...prev,
                userMessage,
                {
                    id: assistantId,
                    role: "assistant",
                    content: "",
                    createdAt: Date.now(),
                },
            ]);

            setIsStreaming(true);
            setError(null);
            setThinking("");

            const controller = new AbortController();
            controllerRef.current = controller;

            let response: Response;
            try {
                response = await fetch(`${API_BASE}/api/chat/stream`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        messages: history,
                        context: options?.context,
                    }),
                    signal: controller.signal,
                });
            } catch (err) {
                setIsStreaming(false);
                setError(err instanceof Error ? err.message : "Network error");
                return;
            }

            if (!response.ok || !response.body) {
                setIsStreaming(false);
                setError(`Request failed (${response.status})`);
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            try {
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const segments = buffer.split("\n\n");
                    buffer = segments.pop() || "";

                    for (const segment of segments) {
                        const evt = parseSSEChunk(segment);
                        if (!evt) continue;

                        if (evt.event === "message") {
                            try {
                                const data = JSON.parse(evt.data);
                                appendAssistantDelta(data.delta ?? "");
                            } catch {
                                // swallow parse errors to keep stream alive
                            }
                        } else if (evt.event === "thinking") {
                            try {
                                const data = JSON.parse(evt.data);
                                setThinking((prev) => prev + (data.delta ?? ""));
                            } catch {
                                // ignore malformed thinking chunks
                            }
                        } else if (evt.event === "error") {
                            try {
                                const data = JSON.parse(evt.data);
                                setError(data.error || "Chat error");
                            } catch {
                                setError("Chat error");
                            }
                        } else if (evt.event === "done") {
                            // No-op; will stop after stream ends
                        }
                    }
                }
            } catch (err) {
                if (controller.signal.aborted) {
                    setError(null);
                } else {
                    setError(err instanceof Error ? err.message : "Streaming error");
                }
            } finally {
                setIsStreaming(false);
                assistantIdRef.current = null;
            }
        },
        [appendAssistantDelta],
    );

    return {
        messages,
        isStreaming,
        error,
        thinking,
        sendMessage,
        stop,
        clear,
    };
}

