import { NextResponse } from "next/server";

// 获取后端 API URL，默认为本地开发环境
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(request: Request) {
  try {
    const { url } = await request.json();

    if (!url) {
      return NextResponse.json({ error: "URL is required" }, { status: 400 });
    }

    // 调用 Python API 服务
    const response = await fetch(`${API_URL}/video-captions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      console.error("API Error:", {
        status: response.status,
        statusText: response.statusText,
        errorData,
      });
      throw new Error(
        `Failed to generate subtitle: ${response.status} ${response.statusText}`
      );
    }

    const data = await response.json();
    console.log("API Response:", data);

    // 确保返回的数据格式正确
    if (!data.title || !Array.isArray(data.subtitles)) {
      console.error("Invalid data format:", data);
      throw new Error("Invalid subtitle data format from server");
    }

    return NextResponse.json(data);
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
