"use client";

import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";
import { ChatPanel } from "@/components/ChatPanel";
import { useState, useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";

export default function MainLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isMobile, setIsMobile] = useState(false);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const pathname = usePathname();

    const searchParams = useSearchParams();

    // Determine title
    let title = "Dashboard";
    if (pathname === "/tasks") {
        const status = searchParams.get("status");
        title = status === "deleted" ? "Bin" : "My Tasks";
    } else if (pathname === "/list") {
        title = "List View";
    } else if (pathname === "/unsorted") {
        title = "Unsorted";
    } else if (pathname === "/simple") {
        title = "Simple View";
    } else if (pathname.startsWith("/analyze")) {
        title = "Analyze Task";
    } else if (pathname.startsWith("/settings")) {
        title = "Settings";
    }

    useEffect(() => {
        const checkMobile = () => {
            const isSmall = window.innerWidth < 768;
            setIsMobile(isSmall);
            if (isSmall) {
                setIsSidebarOpen(false);
                setIsChatOpen(false);
            } else {
                setIsSidebarOpen(true);
                setIsChatOpen(true);
            }
        };

        checkMobile();
        window.addEventListener("resize", checkMobile);
        return () => window.removeEventListener("resize", checkMobile);
    }, []);

    return (
        <div className="flex h-screen overflow-hidden bg-background text-foreground">
            <Sidebar
                isOpen={isSidebarOpen}
                setIsOpen={setIsSidebarOpen}
                isMobile={isMobile}
            />

            <div className="flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out relative">
                <TopBar
                    onMenuClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    onChatToggle={() => setIsChatOpen(!isChatOpen)}
                    chatOpen={isChatOpen}
                    title={title}
                />

                <div className="flex flex-1 overflow-hidden">
                    <main className="flex-1 overflow-y-auto p-6 md:p-8">
                        <div className="mx-auto max-w-5xl animate-in fade-in slide-in-from-bottom-4 duration-500">
                            {children}
                        </div>
                    </main>

                    <div
                        className={`relative h-full transition-all duration-200 ${isChatOpen ? (isMobile ? "w-full" : "w-[360px]") : "w-0"
                            }`}
                    >
                        <ChatPanel
                            isOpen={isChatOpen}
                            onClose={() => setIsChatOpen(false)}
                            isMobile={isMobile}
                            context={{ pathname }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
