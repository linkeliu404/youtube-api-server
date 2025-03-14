"use client";

import { useState, FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [useBackupApi, setUseBackupApi] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);

    try {
      // 尝试使用主 API
      let apiEndpoint = "/api/subtitle";

      // 如果上次失败或用户选择了备用 API，则使用备用 API
      if (useBackupApi) {
        apiEndpoint = "/api/direct-subtitle";
      }

      const response = await fetch(apiEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      const data = await response.json();
      console.log("Received data:", data);

      if (!response.ok) {
        // 如果主 API 失败，尝试使用备用 API
        if (!useBackupApi && apiEndpoint === "/api/subtitle") {
          setUseBackupApi(true);
          throw new Error(
            `${data.error || "Failed to fetch subtitle"} - Trying backup API...`
          );
        } else {
          throw new Error(data.error || "Failed to fetch subtitle");
        }
      }

      if (data.error) {
        throw new Error(data.error);
      }

      if (!data.title || !Array.isArray(data.subtitles)) {
        console.error("Invalid data format:", data);
        throw new Error(`Invalid data format: ${JSON.stringify(data)}`);
      }

      // 将数据存储在 localStorage 中
      localStorage.setItem("subtitleData", JSON.stringify(data));

      // 在新标签页打开结果
      window.open("/result", "_blank");

      toast.success("Subtitle generated successfully!");
    } catch (error) {
      console.error("Error:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Failed to generate subtitle";
      toast.error(errorMessage);

      // 如果错误消息包含 "Trying backup API"，则自动重试
      if (errorMessage.includes("Trying backup API")) {
        setTimeout(() => {
          handleSubmit(e);
        }, 1000);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-4 md:p-24 bg-gradient-to-b from-background to-muted">
      <Card className="w-full max-w-[800px] shadow-lg mb-8">
        <CardHeader className="space-y-1">
          <CardTitle className="text-3xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            YouTube Subtitle Generator
          </CardTitle>
          <CardDescription className="text-lg">
            Generate subtitles from any YouTube video
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">YouTube URL</label>
              <Input
                type="url"
                placeholder="https://www.youtube.com/watch?v=..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                className="h-12 text-lg"
              />
            </div>
            <Button
              type="submit"
              className="w-full h-12 text-lg font-semibold"
              disabled={loading}
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Generating...
                </div>
              ) : (
                "Generate Subtitle"
              )}
            </Button>
            <div className="text-xs text-center text-muted-foreground">
              {useBackupApi
                ? "Using direct API (client-side processing)"
                : "Using backend API"}
            </div>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
