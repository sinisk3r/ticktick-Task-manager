"use client"

import { useEditor, EditorContent, Editor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Typography from '@tiptap/extension-typography'
import { Markdown } from 'tiptap-markdown'
import { Bold, Italic, List, ListOrdered, Link, Heading1, Heading2, Quote, Code, RotateCcw, RotateCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useEffect } from 'react'

// Extend the Editor storage type to include markdown
declare module '@tiptap/core' {
    interface Commands<ReturnType> {
        markdown: {
            /**
             * Get the document as markdown
             */
            getMarkdown: () => string
        }
    }
}

interface TipTapEditorProps {
    value: string
    onChange: (value: string) => void
    editable?: boolean
}

const ToolbarButton = ({
    onClick,
    isActive = false,
    disabled = false,
    children,
    title
}: {
    onClick: () => void,
    isActive?: boolean,
    disabled?: boolean,
    children: React.ReactNode,
    title?: string
}) => (
    <Button
        variant={isActive ? "secondary" : "ghost"}
        size="icon"
        onClick={onClick}
        disabled={disabled}
        className={cn("h-7 w-7", isActive && "bg-muted text-primary")}
        title={title}
        type="button"
    >
        {children}
    </Button>
)

const TipTapToolbar = ({ editor }: { editor: Editor | null }) => {
    if (!editor) return null

    return (
        <div className="flex items-center gap-0.5 p-1 border-b bg-muted/40 sticky top-0 z-10">
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleBold().run()}
                disabled={!editor.can().chain().focus().toggleBold().run()}
                isActive={editor.isActive('bold')}
                title="Bold (Cmd+B)"
            >
                <Bold className="size-3.5" />
            </ToolbarButton>
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleItalic().run()}
                disabled={!editor.can().chain().focus().toggleItalic().run()}
                isActive={editor.isActive('italic')}
                title="Italic (Cmd+I)"
            >
                <Italic className="size-3.5" />
            </ToolbarButton>

            <div className="w-px h-4 bg-border mx-1" />

            <ToolbarButton
                onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                isActive={editor.isActive('heading', { level: 1 })}
                title="Heading 1"
            >
                <Heading1 className="size-3.5" />
            </ToolbarButton>
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                isActive={editor.isActive('heading', { level: 2 })}
                title="Heading 2"
            >
                <Heading2 className="size-3.5" />
            </ToolbarButton>

            <div className="w-px h-4 bg-border mx-1" />

            <ToolbarButton
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                isActive={editor.isActive('bulletList')}
                title="Bullet List"
            >
                <List className="size-3.5" />
            </ToolbarButton>
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
                isActive={editor.isActive('orderedList')}
                title="Ordered List"
            >
                <ListOrdered className="size-3.5" />
            </ToolbarButton>

            <div className="w-px h-4 bg-border mx-1" />

            <ToolbarButton
                onClick={() => editor.chain().focus().toggleBlockquote().run()}
                isActive={editor.isActive('blockquote')}
                title="Quote"
            >
                <Quote className="size-3.5" />
            </ToolbarButton>
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleCodeBlock().run()}
                isActive={editor.isActive('codeBlock')}
                title="Code Block"
            >
                <Code className="size-3.5" />
            </ToolbarButton>

            <div className="w-px h-4 bg-border mx-1" />

            <ToolbarButton
                onClick={() => editor.chain().focus().undo().run()}
                disabled={!editor.can().chain().focus().undo().run()}
                title="Undo"
            >
                <RotateCcw className="size-3.5" />
            </ToolbarButton>
            <ToolbarButton
                onClick={() => editor.chain().focus().redo().run()}
                disabled={!editor.can().chain().focus().redo().run()}
                title="Redo"
            >
                <RotateCw className="size-3.5" />
            </ToolbarButton>

        </div>
    )
}

export function TipTapEditor({ value, onChange, editable = true }: TipTapEditorProps) {
    const editor = useEditor({
        immediatelyRender: false,
        extensions: [
            StarterKit.configure({
                bulletList: {
                    keepMarks: true,
                    keepAttributes: false,
                },
                orderedList: {
                    keepMarks: true,
                    keepAttributes: false,
                },
            }),
            Typography,
            Markdown,
        ],
        content: value,
        editorProps: {
            attributes: {
                class: 'prose prose-sm dark:prose-invert focus:outline-none max-w-none min-h-[300px] p-4',
            },
        },
        onUpdate: ({ editor }) => {
            // Safe cast as we know the extension is added
            onChange((editor.storage.markdown as any).getMarkdown())
        },
    })

    // Sync value changes from outside (e.g. init or remote update)
    useEffect(() => {
        if (editor && value) {
            const currentMarkdown = (editor.storage.markdown as any).getMarkdown()
            if (currentMarkdown !== value) {
                // Heuristic: if length changed significantly (likely an Enhance replace), update it.
                if (editor.isEmpty) {
                    editor.commands.setContent(value)
                } else if (Math.abs(currentMarkdown.length - value.length) > 5) {
                    editor.commands.setContent(value)
                }
            }
        }
    }, [value, editor])

    return (
        <div className="flex flex-col h-full border rounded-md overflow-hidden bg-background">
            <TipTapToolbar editor={editor} />
            <EditorContent editor={editor} className="flex-1 overflow-y-auto" />
        </div>
    )
}
