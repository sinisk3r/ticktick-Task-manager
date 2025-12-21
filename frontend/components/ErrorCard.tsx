"use client";

import React, { useState } from "react";
import { AlertTriangle, ChevronRight, Code, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorCardProps {
    error: string;
    errorData?: Record<string, any>;
    onViewDetails?: () => void;
    className?: string;
}

// Simple markdown renderer (similar to renderMarkdownLite in ChatPanel)
const renderMarkdownLite = (value: string) => {
    const escapeHtml = (text: string) =>
        text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");

    let html = escapeHtml(value);
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
    html = html.replace(/`(.+?)`/g, "<code class='bg-muted px-1 py-0.5 rounded text-xs'>$1</code>");
    html = html.replace(/\n/g, "<br>");
    return html;
};

// Extract a user-friendly error summary
const extractErrorSummary = (error: string, errorData?: Record<string, any>): string => {
    // Try to parse JSON error messages
    try {
        const parsed = JSON.parse(error);
        if (parsed.error?.message) {
            return parsed.error.message;
        } else if (parsed.message) {
            return parsed.message;
        }
    } catch {
        // Not JSON, try errorData
        if (errorData?.parsed_error?.error?.message) {
            return errorData.parsed_error.error.message;
        } else if (errorData?.user_message) {
            return errorData.user_message;
        } else if (errorData?.message) {
            return errorData.message;
        }
    }

    // Try to extract from error string patterns
    const patterns = [
        /Error calling model '([^']+)' \(([^)]+)\): (.+)/,
        /(\d{3}) (.+)/,
        /(.+?): (.+)/,
    ];

    for (const pattern of patterns) {
        const match = error.match(pattern);
        if (match) {
            return match[match.length - 1]; // Return the last capture group
        }
    }

    // Fallback: return first line or first 200 chars
    const firstLine = error.split("\n")[0];
    return firstLine.length > 200 ? firstLine.substring(0, 200) + "..." : firstLine;
};

// Format full error text
const formatErrorText = (error: string, errorData?: Record<string, any>, formatted: boolean = true): string => {
    if (!formatted) {
        return error;
    }

    // Try to parse and format JSON errors
    try {
        const parsed = JSON.parse(error);
        return formatObject(parsed, 0);
    } catch {
        if (errorData?.parsed_error) {
            return formatObject(errorData.parsed_error, 0);
        }
    }

    // Format as markdown-friendly text
    return error
        .replace(/\n\n+/g, "\n\n") // Normalize multiple newlines
        .replace(/^(\d{3}) (.+)$/gm, "**$1** $2") // Format HTTP status codes
        .replace(/^([A-Z_]+): (.+)$/gm, "**$1:** $2") // Format key-value pairs
        .replace(/`([^`]+)`/g, "`$1`"); // Preserve code blocks
}

const formatObject = (obj: any, indent: number = 0): string => {
    if (typeof obj === "string") {
        return obj;
    }
    if (obj === null || obj === undefined) {
        return String(obj);
    }
    if (Array.isArray(obj)) {
        return obj.map((item, idx) => `${"  ".repeat(indent)}- ${formatObject(item, indent + 1)}`).join("\n");
    }
    if (typeof obj === "object") {
        return Object.entries(obj)
            .map(([key, value]) => {
                const formattedValue = typeof value === "object" && value !== null
                    ? `\n${formatObject(value, indent + 1)}`
                    : String(value);
                return `${"  ".repeat(indent)}**${key}:** ${formattedValue}`;
            })
            .join("\n");
    }
    return String(obj);
};

export function ErrorCard({ error, errorData, onViewDetails, className }: ErrorCardProps) {
    const [formatted, setFormatted] = useState(true);
    const [expanded, setExpanded] = useState(false);
    
    const summary = extractErrorSummary(error, errorData);
    const hasDetails = !!(errorData && Object.keys(errorData).length > 0) || error.length > summary.length;
    
    // Truncate to 100 characters for preview
    const MAX_PREVIEW_LENGTH = 100;
    const shouldTruncate = summary.length > MAX_PREVIEW_LENGTH;
    const displayText = expanded || !shouldTruncate 
        ? summary 
        : summary.substring(0, MAX_PREVIEW_LENGTH) + "...";

    return (
        <div
            className={cn(
                "rounded-lg border border-destructive/50 bg-destructive/10 p-3 space-y-2",
                className
            )}
        >
            <div className="flex items-start gap-2">
                <AlertTriangle className="size-4 text-destructive mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-destructive">Error</p>
                    <div
                        className="text-sm text-destructive/90 mt-1 break-words prose prose-invert prose-p:my-0 prose-ul:my-1 prose-li:my-0 prose-strong:text-destructive prose-code:text-destructive/80"
                        dangerouslySetInnerHTML={{
                            __html: renderMarkdownLite(displayText),
                        }}
                    />
                    {shouldTruncate && (
                        <button
                            type="button"
                            onClick={(e) => {
                                e.stopPropagation();
                                setExpanded(!expanded);
                            }}
                            className="text-xs text-destructive/80 hover:text-destructive mt-1 underline"
                        >
                            {expanded ? "Show less" : "Show more"}
                        </button>
                    )}
                </div>
            </div>
            
            <div className="flex items-center justify-between gap-2 pt-1 border-t border-destructive/20">
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                            e.stopPropagation();
                            setFormatted(!formatted);
                        }}
                        className="h-7 px-2 text-xs text-destructive/80 hover:text-destructive hover:bg-destructive/20"
                    >
                        {formatted ? (
                            <>
                                <Code className="size-3 mr-1" />
                                Formatted
                            </>
                        ) : (
                            <>
                                <FileText className="size-3 mr-1" />
                                Raw
                            </>
                        )}
                    </Button>
                </div>
                {hasDetails && onViewDetails && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                            e.stopPropagation();
                            onViewDetails();
                        }}
                        className="h-7 px-2 text-xs text-destructive hover:text-destructive hover:bg-destructive/20"
                    >
                        <span>View full details</span>
                        <ChevronRight className="size-3 ml-1" />
                    </Button>
                )}
            </div>
        </div>
    );
}

