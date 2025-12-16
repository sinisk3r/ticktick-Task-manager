"use client"

import { useState, lazy, Suspense } from "react"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp, Loader2 } from "lucide-react"
import { DescriptionPreview } from "@/components/DescriptionPreview"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"

// Lazy load TipTapEditor for performance
const TipTapEditor = lazy(() => import("@/components/TipTapEditor").then(mod => ({ default: mod.TipTapEditor })))

interface CollapsibleDescriptionProps {
    value: string
    onChange: (value: string) => void
    className?: string
}

export function CollapsibleDescription({
    value,
    onChange,
    className
}: CollapsibleDescriptionProps) {
    const [isExpanded, setIsExpanded] = useState(false)
    const hasContent = value && value.trim() !== ""

    return (
        <div className={cn("flex flex-col h-full", className)}>
            <AnimatePresence mode="wait">
                {!isExpanded ? (
                    <motion.div
                        key="preview"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="flex-1 p-4 space-y-3"
                    >
                        {hasContent ? (
                            <>
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    <DescriptionPreview markdown={value} maxLines={3} />
                                </div>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="w-full gap-2 text-muted-foreground hover:text-foreground"
                                    onClick={() => setIsExpanded(true)}
                                >
                                    <ChevronDown className="size-4" />
                                    Expand description
                                </Button>
                            </>
                        ) : (
                            <div className="flex items-center justify-center h-full">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="gap-2 text-muted-foreground"
                                    onClick={() => setIsExpanded(true)}
                                >
                                    <ChevronDown className="size-4" />
                                    Add description
                                </Button>
                            </div>
                        )}
                    </motion.div>
                ) : (
                    <motion.div
                        key="editor"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="flex-1 flex flex-col h-full"
                    >
                        <div className="flex items-center justify-between p-2 px-4 border-b">
                            <span className="text-xs font-medium text-muted-foreground">
                                Description
                            </span>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 gap-2 text-xs"
                                onClick={() => setIsExpanded(false)}
                            >
                                <ChevronUp className="size-3" />
                                Collapse
                            </Button>
                        </div>

                        <Suspense
                            fallback={
                                <div className="flex-1 flex items-center justify-center p-8">
                                    <Loader2 className="size-6 animate-spin text-muted-foreground" />
                                </div>
                            }
                        >
                            <TipTapEditor
                                value={value}
                                onChange={onChange}
                            />
                        </Suspense>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
