"use client";

import React, { useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { AlertTriangle, Code, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorDetailsDialogProps {
    isOpen: boolean;
    onClose: () => void;
    error: string;
    errorData?: Record<string, any>;
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
    html = html.replace(/`(.+?)`/g, "<code class='bg-muted px-1 py-0.5 rounded text-xs font-mono'>$1</code>");
    html = html.replace(/\n/g, "<br>");
    return html;
};

// Format error as markdown
const formatErrorMarkdown = (error: string, errorData?: Record<string, any>): string => {
    // Try to parse and format JSON errors
    try {
        const parsed = JSON.parse(error);
        return formatObjectMarkdown(parsed, 0);
    } catch {
        if (errorData?.parsed_error) {
            return formatObjectMarkdown(errorData.parsed_error, 0);
        }
    }

    // Format as markdown-friendly text
    return error
        .replace(/\n\n+/g, "\n\n") // Normalize multiple newlines
        .replace(/^(\d{3}) (.+)$/gm, "**$1** $2") // Format HTTP status codes
        .replace(/^([A-Z_]+): (.+)$/gm, "**$1:** $2") // Format key-value pairs
        .replace(/`([^`]+)`/g, "`$1`"); // Preserve code blocks
};

const formatObjectMarkdown = (obj: any, indent: number = 0): string => {
    if (typeof obj === "string") {
        return obj;
    }
    if (obj === null || obj === undefined) {
        return String(obj);
    }
    if (Array.isArray(obj)) {
        return obj.map((item, idx) => `${"  ".repeat(indent)}- ${formatObjectMarkdown(item, indent + 1)}`).join("\n");
    }
    if (typeof obj === "object") {
        return Object.entries(obj)
            .map(([key, value]) => {
                const formattedValue = typeof value === "object" && value !== null
                    ? `\n${formatObjectMarkdown(value, indent + 1)}`
                    : String(value);
                return `${"  ".repeat(indent)}**${key}:** ${formattedValue}`;
            })
            .join("\n");
    }
    return String(obj);
};

// Format error as raw text
const formatErrorRaw = (error: string, errorData?: Record<string, any>): string => {
    // Try to parse and format JSON errors
    let parsedError: any = null;
    
    try {
        parsedError = JSON.parse(error);
    } catch {
        if (errorData?.parsed_error) {
            parsedError = errorData.parsed_error;
        } else if (errorData) {
            parsedError = errorData;
        }
    }

    // If we have a nested error structure, extract it
    if (parsedError?.error) {
        parsedError = parsedError.error;
    }

    // Format the error for display
    const formatError = (err: any, indent = 0): string => {
        if (typeof err === "string") {
            return err;
        }
        if (err === null || err === undefined) {
            return String(err);
        }
        if (Array.isArray(err)) {
            return err.map((item, idx) => `${"  ".repeat(indent)}[${idx}]: ${formatError(item, indent + 1)}`).join("\n");
        }
        if (typeof err === "object") {
            return Object.entries(err)
                .map(([key, value]) => {
                    const formattedValue = typeof value === "object" && value !== null
                        ? `\n${formatError(value, indent + 1)}`
                        : String(value);
                    return `${"  ".repeat(indent)}${key}: ${formattedValue}`;
                })
                .join("\n");
        }
        return String(err);
    };

    return parsedError ? formatError(parsedError) : error;
};

export function ErrorDetailsDialog({
    isOpen,
    onClose,
    error,
    errorData,
}: ErrorDetailsDialogProps) {
    const [formatted, setFormatted] = useState(true);

    const displayError = formatted
        ? formatErrorMarkdown(error, errorData)
        : formatErrorRaw(error, errorData);

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-2xl max-h-[80vh]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <AlertTriangle className="size-5 text-destructive" />
                        Error Details
                    </DialogTitle>
                    <DialogDescription>
                        Detailed error information for debugging
                    </DialogDescription>
                </DialogHeader>
                <div className="flex items-center justify-between mb-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setFormatted(!formatted)}
                        className="h-8 px-2 text-xs"
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
                <div className="max-h-[60vh] overflow-auto rounded-md border p-4 bg-muted/50">
                    {formatted ? (
                        <div
                            className="prose prose-invert prose-p:my-0 prose-ul:my-1 prose-li:my-0 prose-strong:text-foreground prose-code:text-foreground/80 text-sm"
                            dangerouslySetInnerHTML={{
                                __html: renderMarkdownLite(displayError),
                            }}
                        />
                    ) : (
                        <pre className="text-xs font-mono whitespace-pre-wrap break-words text-foreground">
                            {displayError}
                        </pre>
                    )}
                </div>
                <div className="flex justify-end">
                    <Button onClick={onClose}>Close</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

