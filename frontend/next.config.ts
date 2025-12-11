import type { NextConfig } from "next";
import * as fs from "fs";
import * as path from "path";

// Load runtime configuration from init.sh if available
const runtimeEnvPath = path.join(__dirname, "..", ".env.runtime");
if (fs.existsSync(runtimeEnvPath)) {
  const envContent = fs.readFileSync(runtimeEnvPath, "utf-8");
  envContent.split("\n").forEach((line) => {
    if (line.startsWith("#") || !line.includes("=")) return;
    const [key, ...valueParts] = line.split("=");
    const value = valueParts.join("=").trim();
    if (key && value) {
      process.env[key] = value;
    }
  });
}

const nextConfig: NextConfig = {
  /* config options here */
  env: {
    // Pass runtime backend URL to client-side code
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || "http://localhost:5400",
  },
};

export default nextConfig;
