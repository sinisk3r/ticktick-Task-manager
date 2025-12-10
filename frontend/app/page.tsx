"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TaskAnalyzer } from "@/components/TaskAnalyzer";
import { LLMSettings } from "@/components/LLMSettings";

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Context Task Management</h1>
        <p className="text-muted-foreground mt-2">
          AI-powered task analysis using the Eisenhower Matrix
        </p>
      </div>

      <Tabs defaultValue="analyze" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="analyze">Analyze Task</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="analyze" className="mt-6">
          <TaskAnalyzer />
        </TabsContent>

        <TabsContent value="settings" className="mt-6">
          <LLMSettings />
        </TabsContent>
      </Tabs>
    </div>
  );
}
