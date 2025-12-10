import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto">
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-3xl">Welcome to Context</CardTitle>
          <CardDescription>
            AI-powered task analysis using the Eisenhower Matrix
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">
            Context is an intelligent task management system that sits on top of TickTick
            to auto-prioritize, schedule, and protect your wellbeing using Claude AI.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Smart Task Intake</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Automatically analyze tasks from TickTick and categorize them using
                  the Eisenhower Matrix (Urgent/Important quadrants).
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Workload Intelligence</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Get insights on your workload, receive rest reminders, and optimize
                  your productivity while protecting your wellbeing.
                </p>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Getting Started</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                1
              </div>
              <div>
                <p className="font-medium">Connect TickTick</p>
                <p className="text-sm text-muted-foreground">
                  Authenticate with your TickTick account to enable task synchronization
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                2
              </div>
              <div>
                <p className="font-medium">Configure Claude AI</p>
                <p className="text-sm text-muted-foreground">
                  Set up your Claude API key for intelligent task analysis
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                3
              </div>
              <div>
                <p className="font-medium">Start Managing Tasks</p>
                <p className="text-sm text-muted-foreground">
                  View your tasks organized by the Eisenhower Matrix and get AI-powered insights
                </p>
              </div>
            </div>
          </div>
          <div className="mt-6">
            <Button>Connect TickTick</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
