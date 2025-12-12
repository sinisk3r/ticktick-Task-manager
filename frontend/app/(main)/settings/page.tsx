"use client";

import { LLMSettings } from "@/components/LLMSettings";
import { TickTickSettings } from "@/components/TickTickSettings";
import { PersonalizationSettings } from "@/components/PersonalizationSettings";
import { ThemeToggle } from "@/components/theme-toggle";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";

export default function SettingsPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                <p className="text-muted-foreground mt-2">
                    Configure AI provider, integrations, and application preferences.
                </p>
            </div>

            <Tabs defaultValue="llm" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="llm">LLM Provider</TabsTrigger>
                    <TabsTrigger value="ticktick">TickTick</TabsTrigger>
                    <TabsTrigger value="personalization">Personalization</TabsTrigger>
                    <TabsTrigger value="appearance">Appearance</TabsTrigger>
                </TabsList>

                <TabsContent value="llm" className="space-y-4 mt-6">
                    <LLMSettings />
                </TabsContent>

                <TabsContent value="ticktick" className="space-y-4 mt-6">
                    <TickTickSettings />
                </TabsContent>

                <TabsContent value="personalization" className="space-y-4 mt-6">
                    <PersonalizationSettings />
                </TabsContent>

                <TabsContent value="appearance" className="space-y-4 mt-6">
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold mb-4">Appearance</h2>
                        <div className="flex items-center justify-between rounded-lg border p-4">
                            <div className="space-y-0.5">
                                <label className="text-base font-medium">Theme</label>
                                <p className="text-sm text-muted-foreground">
                                    Select the theme for the application.
                                </p>
                            </div>
                            <ThemeToggle />
                        </div>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
