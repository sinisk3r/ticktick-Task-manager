"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

export type AgentEventType =
  | "thinking"
  | "step"
  | "tool_request"
  | "tool_result"
  | "message"
  | "message_chunk"  // New: streaming text chunks
  | "done"
  | "error";

export interface AgentEvent {
  id: string;
  type: AgentEventType;
  data: Record<string, any>;
  createdAt: number;
  // For message_chunk events, store the text content directly
  text?: string;
}

export type AgentRole = "user" | "assistant";

export interface AgentMessage {
  id: string;
  role: AgentRole;
  content: string;
  createdAt: number;
  events: AgentEvent[];
  payload?: Record<string, any>;
}

export interface PendingAction {
  tool: string;
  args: Record<string, any>;
  traceId?: string;
}

interface SendOptions {
  context?: Record<string, unknown>;
  dryRun?: boolean;
  userId?: number;
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

export function useAgentStream() {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorData, setErrorData] = useState<Record<string, any> | null>(null);
  const [thinking, setThinking] = useState("");
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);

  const controllerRef = useRef<AbortController | null>(null);
  const assistantIdRef = useRef<string | null>(null);
  const traceIdRef = useRef<string | null>(null);
  const messagesRef = useRef<AgentMessage[]>([]);

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
    setErrorData(null);
    setThinking("");
    setPendingAction(null);
  }, []);

  const appendAssistantEvent = useCallback((event: AgentEvent) => {
    if (!assistantIdRef.current) return;
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === assistantIdRef.current ? { ...msg, events: [...msg.events, event] } : msg,
      ),
    );
  }, []);

  const updateAssistantContent = useCallback((content: string, payload?: Record<string, any>) => {
    if (!assistantIdRef.current) return;
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === assistantIdRef.current
          ? {
              ...msg,
              content: msg.content ? `${msg.content}\n${content}` : content,
              payload: payload ? { ...(msg.payload || {}), ...payload } : msg.payload,
            }
          : msg,
      ),
    );
  }, []);

  const appendAssistantContentDelta = useCallback((delta: string) => {
    if (!assistantIdRef.current) return;
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === assistantIdRef.current
          ? {
              ...msg,
              content: msg.content + delta,
            }
          : msg,
      ),
    );
  }, []);

  const sendGoal = useCallback(
    async (goal: string, options?: SendOptions) => {
      const trimmed = goal.trim();
      if (!trimmed) return;

      const userMessage: AgentMessage = {
        id: newId(),
        role: "user",
        content: trimmed,
        createdAt: Date.now(),
        events: [],
      };

      const assistantId = newId();
      assistantIdRef.current = assistantId;
      traceIdRef.current = null;

      // Capture conversation history before updating state
      const conversationHistory = messagesRef.current.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

      setMessages((prev) => [
        ...prev,
        userMessage,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          createdAt: Date.now(),
          events: [],
        },
      ]);

      setIsStreaming(true);
      setError(null);
      setErrorData(null);
      setThinking("");
      setPendingAction(null);

      const controller = new AbortController();
      controllerRef.current = controller;

      let response: Response;
      try {
        response = await fetch(`${API_BASE}/api/agent/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            goal: trimmed,
            messages: conversationHistory,
            context: options?.context,
            dry_run: options?.dryRun ?? false,
            user_id: options?.userId ?? 1,
            use_v2_agent: true, // Enable Chat UX v2 with personalization and memory
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

            let data: Record<string, any> = {};
            try {
              data = JSON.parse(evt.data);
            } catch {
              // ignore parse errors for malformed chunks
            }

            if (data.trace_id && !traceIdRef.current) {
              traceIdRef.current = data.trace_id;
            }

            const agentEvent: AgentEvent = {
              id: newId(),
              type: evt.event as AgentEventType,
              data,
              createdAt: Date.now(),
            };

            switch (evt.event) {
              case "thinking":
                setThinking((prev) => prev + (data.text || data.delta || ""));
                appendAssistantEvent(agentEvent);
                break;
              case "step":
              case "tool_request":
              case "tool_result":
                appendAssistantEvent(agentEvent);
                if (
                  evt.event === "tool_request" &&
                  data.confirmation_required &&
                  !(data.args || {}).confirm
                ) {
                  setPendingAction({
                    tool: data.tool,
                    args: data.args || {},
                    traceId: data.trace_id || traceIdRef.current || undefined,
                  });
                }
                if (evt.event === "tool_result" && data.result?.payload) {
                  updateAssistantContent("", data.result.payload);
                }
                break;
              case "message":
                // Handle both streaming deltas and complete messages
                if (typeof data.delta === "string") {
                  // Streaming mode - append delta to content AND add as event for chronological ordering
                  appendAssistantContentDelta(data.delta);
                  // Store the text chunk in the event for proper ordering
                  appendAssistantEvent({
                    ...agentEvent,
                    type: "message_chunk",
                    text: data.delta,
                  });
                } else if (typeof data.message === "string") {
                  // Complete message - add as new line
                  updateAssistantContent(data.message, data.payload);
                  appendAssistantEvent({
                    ...agentEvent,
                    text: data.message,
                  });
                }
                break;
              case "error":
                setError(data.message || "Agent error");
                setErrorData(data);
                appendAssistantEvent(agentEvent);
                
                // Add error as an assistant message in the chat flow
                const errorMessage: AgentMessage = {
                  id: newId(),
                  role: "assistant",
                  content: data.message || "An error occurred",
                  createdAt: Date.now(),
                  events: [agentEvent],
                  payload: { error: true, errorData: data },
                };
                setMessages((prev) => [...prev, errorMessage]);
                break;
              case "done":
                appendAssistantEvent(agentEvent);
                break;
              default:
                break;
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
      }
    },
    [appendAssistantEvent, updateAssistantContent, appendAssistantContentDelta],
  );

  const executePending = useCallback(
    async (action: "confirm" | "cancel") => {
      if (!pendingAction) return;
      if (action === "cancel") {
        setPendingAction(null);
        appendAssistantEvent({
          id: newId(),
          type: "message",
          data: { message: "Action cancelled." },
          createdAt: Date.now(),
        });
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/api/agent/execute`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tool: pendingAction.tool,
            args: { ...pendingAction.args, confirm: true },
            user_id: (pendingAction.args.user_id as number) || 1,
            trace_id: pendingAction.traceId,
          }),
        });

        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || `Execution failed (${response.status})`);
        }

        const data = await response.json();
        appendAssistantEvent({
          id: newId(),
          type: "tool_result",
          data: { trace_id: data.trace_id, tool: data.tool, result: data.result },
          createdAt: Date.now(),
        });
        if (data.result?.summary) {
          updateAssistantContent(data.result.summary, data.result.payload);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Execution error");
      } finally {
        setPendingAction(null);
      }
    },
    [appendAssistantEvent, pendingAction, updateAssistantContent],
  );

  return {
    messages,
    isStreaming,
    error,
    errorData,
    thinking,
    pendingAction,
    sendGoal,
    stop,
    clear,
    executePending,
  };
}

