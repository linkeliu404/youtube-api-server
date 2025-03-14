"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

interface Subtitle {
  text: string;
  timestamp: string;
  start: number;
  duration: number;
}

interface ResultData {
  title: string;
  subtitles: Subtitle[];
}

export default function ResultPage() {
  const [data, setData] = useState<ResultData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const storedData = localStorage.getItem("subtitleData");
      if (!storedData) {
        setError("No subtitle data found. Please generate subtitles first.");
        return;
      }

      const parsedData = JSON.parse(storedData) as ResultData;
      setData(parsedData);
    } catch (err) {
      console.error("Error loading data:", err);
      setError("Failed to load subtitle data");
    }
  }, []);

  const handleDownload = () => {
    if (!data || !data.subtitles.length) return;

    const srtContent = data.subtitles
      .map((subtitle, index) => {
        const startTime = new Date(subtitle.start * 1000)
          .toISOString()
          .substr(11, 8)
          .replace(".", ",");
        const endTime = new Date((subtitle.start + subtitle.duration) * 1000)
          .toISOString()
          .substr(11, 8)
          .replace(".", ",");
        return `${index + 1}\n${startTime} --> ${endTime}\n${
          subtitle.text
        }\n\n`;
      })
      .join("");

    const blob = new Blob([srtContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.title || "subtitle"}.srt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-4">
        <div className="text-destructive text-center">
          <h1 className="text-2xl font-bold mb-2">Error</h1>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-4">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-4">Loading subtitles...</p>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center p-6 md:p-12 bg-background">
      <div className="w-full max-w-[1000px]">
        <div className="flex flex-col mb-8">
          <h1 className="text-3xl font-bold text-primary mb-4">{data.title}</h1>
          <Button
            onClick={handleDownload}
            variant="outline"
            size="lg"
            className="gap-2 self-start"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Download SRT
          </Button>
        </div>

        <div className="space-y-4">
          {data.subtitles.map((subtitle, index) => (
            <div
              key={index}
              className="flex items-start gap-4 p-3 rounded-md hover:bg-muted/30 transition-colors"
            >
              <span className="text-sm font-mono text-muted-foreground whitespace-nowrap pt-1 min-w-[60px]">
                {subtitle.timestamp}
              </span>
              <p className="text-base leading-relaxed">{subtitle.text}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
