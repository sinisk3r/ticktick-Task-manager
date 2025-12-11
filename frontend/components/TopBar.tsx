"use client";

import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import Image from "next/image";

interface TopBarProps {
    onMenuClick: () => void;
    title?: string;
}

export function TopBar({ onMenuClick, title }: TopBarProps) {
    return (
        <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b bg-background/80 backdrop-blur px-6 shadow-sm">
            <Button
                variant="ghost"
                size="icon"
                className="md:hidden -ml-2 text-muted-foreground hover:text-foreground"
                onClick={onMenuClick}
            >
                <Menu className="size-6" />
                <span className="sr-only">Toggle sidebar</span>
            </Button>

            <div className="flex items-center gap-2">
                {/* Breadcrumb or Page Title area - can be dynamic later */}
                <h2 className="text-lg font-semibold tracking-tight text-foreground">{title || "Dashboard"}</h2>
            </div>

            <div className="ml-auto flex items-center gap-4">
                {/* Actions like notifications can go here */}
            </div>
        </header>
    );
}
