"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

/**
 * OAuth Callback Page
 *
 * This page handles the OAuth callback redirect from TickTick after user authorization.
 * It displays the authentication status and redirects the user back to the main application.
 *
 * Query Parameters:
 * - status: "success" or "error"
 * - message: Success or error message to display
 */
export default function AuthCallback() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [countdown, setCountdown] = useState(3);

  const status = searchParams.get("status");
  const message = searchParams.get("message") || "Processing authentication...";

  useEffect(() => {
    // Start countdown timer
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          // Redirect to home page after countdown
          router.push("/");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [router]);

  const isSuccess = status === "success";
  const isError = status === "error";
  const isProcessing = !isSuccess && !isError;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {isProcessing && <Loader2 className="h-5 w-5 animate-spin" />}
            {isSuccess && <CheckCircle2 className="h-5 w-5 text-green-500" />}
            {isError && <XCircle className="h-5 w-5 text-red-500" />}
            {isProcessing && "Authenticating..."}
            {isSuccess && "Authentication Successful"}
            {isError && "Authentication Failed"}
          </CardTitle>
          <CardDescription>
            {isProcessing && "Please wait while we complete the authentication process."}
            {(isSuccess || isError) && `Redirecting in ${countdown} seconds...`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Alert variant={isError ? "destructive" : "default"}>
            <AlertDescription className="text-sm">
              {message}
            </AlertDescription>
          </Alert>

          {(isSuccess || isError) && (
            <div className="mt-4 text-center">
              <button
                onClick={() => router.push("/")}
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                Click here if you are not redirected automatically
              </button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
