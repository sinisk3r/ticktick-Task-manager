"use client";

import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  CheckSquare,
  Settings,
  Menu,
  X,
  Plus,
  BrainCircuit,
  User,
  Inbox,
  ListTodo,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import useSWR from "swr";

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  isMobile: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function Sidebar({ isOpen, setIsOpen, isMobile }: SidebarProps) {
  const pathname = usePathname();

  // Fetch unsorted count
  const { data: unsortedData } = useSWR(
    `${API_BASE}/api/tasks/unsorted?user_id=1`,
    fetcher,
    { refreshInterval: 10000 }
  );
  const unsortedCount = unsortedData?.total || 0;

  const navItems = [
    {
      title: "Analyze Task",
      href: "/analyze",
      icon: BrainCircuit,
      variant: "default",
    },
    {
      title: "My Tasks",
      href: "/tasks",
      icon: CheckSquare,
      variant: "default",
    },
    {
      title: "List View",
      href: "/list",
      icon: ListTodo,
      variant: "default",
    },
    {
      title: "Unsorted",
      href: "/unsorted",
      icon: Inbox,
      variant: "default",
      badge: unsortedCount > 0 ? unsortedCount : undefined,
    },
    {
      title: "Simple View",
      href: "/simple",
      icon: ListTodo,
      variant: "default",
    },
    {
      title: "Settings",
      href: "/settings",
      icon: Settings,
      variant: "ghost",
    },
  ];

  return (
    <>
      <AnimatePresence>
        {(isOpen || !isMobile) && (
          <motion.div
            initial={{ x: -280, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -280, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className={cn(
              "fixed inset-y-0 left-0 z-40 w-72 bg-sidebar border-r border-sidebar-border flex flex-col",
              isMobile ? "shadow-2xl" : "relative"
            )}
          >
            {/* Header */}
            <div className="p-4 flex items-center justify-between border-b border-sidebar-border">
              <div className="flex items-center gap-2 font-semibold text-xl text-sidebar-foreground">
                <div className="size-8 rounded-lg bg-sidebar-primary flex items-center justify-center text-sidebar-primary-foreground">
                  <LayoutDashboard className="size-5" />
                </div>
                <span>Context</span>
              </div>
              {isMobile && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  onClick={() => setIsOpen(false)}
                >
                  <X className="size-5" />
                </Button>
              )}
            </div>

            {/* User Profile Snippet */}
            <div className="p-4">
              <div className="flex items-center gap-3 p-3 rounded-xl bg-sidebar-accent/50 hover:bg-sidebar-accent transition-colors cursor-pointer group">
                <div className="size-10 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white shadow-md">
                  <User className="size-5" />
                </div>
                <div className="flex flex-col overflow-hidden">
                  <span className="text-sm font-medium text-sidebar-foreground truncate">User</span>
                  <span className="text-xs text-muted-foreground truncate">Pro Plan</span>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 py-2 space-y-1 overflow-y-auto custom-scrollbar">
              {navItems.map((item) => {
                const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => isMobile && setIsOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group relative overflow-hidden",
                      isActive
                        ? "text-sidebar-primary-foreground bg-sidebar-primary shadow-md shadow-sidebar-primary/20"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    )}
                  >
                    <item.icon className={cn("size-5", isActive ? "text-sidebar-primary-foreground" : "text-muted-foreground group-hover:text-sidebar-accent-foreground")} />
                    <span className="flex-1">{item.title}</span>
                    {item.badge !== undefined && (
                      <span className="ml-auto px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-600 text-white">
                        {item.badge}
                      </span>
                    )}
                    {isActive && (
                      <motion.div
                        layoutId="activeNav"
                        className="absolute right-2 w-1.5 h-1.5 rounded-full bg-white/40"
                      />
                    )}
                  </Link>
                )
              })}
            </nav>

            {/* Quick Actions (Bottom) */}
            <div className="p-4 border-t border-sidebar-border">
              {/* Could add quick add task here later */}
              <Button className="w-full justify-start gap-2 shadow-sm" size="lg">
                <Plus className="size-5" />
                <span className="font-medium">New Task</span>
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Overlay for mobile */}
      {isMobile && isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setIsOpen(false)}
          className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm"
        />
      )}
    </>
  );
}
