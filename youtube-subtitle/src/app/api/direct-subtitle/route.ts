import { NextResponse } from "next/server";

// 注意：需要先安装 youtube-transcript 包
// npm install youtube-transcript

interface TranscriptItem {
  text: string;
  duration: number;
  offset: number;
  start: number;
}

export async function POST(request: Request) {
  try {
    const { url } = await request.json();

    if (!url) {
      return NextResponse.json({ error: "URL is required" }, { status: 400 });
    }

    console.log(`Fetching subtitles directly for URL: ${url}`);

    // 从 URL 提取视频 ID
    const videoId = extractVideoId(url);
    if (!videoId) {
      return NextResponse.json(
        { error: "Invalid YouTube URL" },
        { status: 400 }
      );
    }

    try {
      // 动态导入 youtube-transcript 包
      const { getSubtitles } = await import("youtube-transcript");

      // 直接获取字幕
      const transcriptItems: TranscriptItem[] = await getSubtitles({
        videoID: videoId,
        lang: "en", // 默认使用英语
      });

      // 格式化字幕
      const formattedCaptions = transcriptItems.map((item) => {
        const start = Math.floor(item.start);
        const minutes = Math.floor(start / 60);
        const seconds = start % 60;
        return {
          text: item.text,
          timestamp: `${minutes}:${seconds.toString().padStart(2, "0")}`,
          start: start,
          duration: item.duration,
        };
      });

      // 获取视频标题（简化版，实际应用中可能需要使用 YouTube API）
      const title = `YouTube Video (${videoId})`;

      return NextResponse.json({
        title,
        subtitles: formattedCaptions,
      });
    } catch (e) {
      console.error("Error fetching subtitles:", e);
      return NextResponse.json(
        {
          error:
            "Failed to fetch subtitles. Try using the backend API instead.",
        },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error("Error details:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to generate subtitle",
      },
      { status: 500 }
    );
  }
}

// 辅助函数：从 YouTube URL 提取视频 ID
function extractVideoId(url: string): string | null {
  try {
    const urlObj = new URL(url);

    // 处理 youtu.be 短链接
    if (urlObj.hostname === "youtu.be") {
      return urlObj.pathname.substring(1);
    }

    // 处理标准 YouTube URL
    if (
      urlObj.hostname === "www.youtube.com" ||
      urlObj.hostname === "youtube.com"
    ) {
      if (urlObj.pathname === "/watch") {
        return urlObj.searchParams.get("v");
      }

      if (urlObj.pathname.startsWith("/embed/")) {
        return urlObj.pathname.split("/")[2];
      }

      if (urlObj.pathname.startsWith("/v/")) {
        return urlObj.pathname.split("/")[2];
      }
    }

    return null;
  } catch (e) {
    console.error("Error parsing URL:", e);
    return null;
  }
}
