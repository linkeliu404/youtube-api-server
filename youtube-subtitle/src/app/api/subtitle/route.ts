import { NextResponse } from "next/server";

// 获取后端 API URL，默认为本地开发环境
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 重试函数
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries = 3,
  backoff = 300
) {
  try {
    const response = await fetch(url, options);

    if (response.ok) {
      return response;
    }

    // 如果是最后一次尝试，直接返回错误响应
    if (retries === 0) {
      return response;
    }

    // 如果是 5xx 错误，进行重试
    if (response.status >= 500) {
      console.log(`Retrying, ${retries} attempts left...`);
      await new Promise((resolve) => setTimeout(resolve, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }

    // 其他错误直接返回
    return response;
  } catch (error) {
    if (retries === 0) {
      throw error;
    }

    console.log(`Network error, retrying... ${retries} attempts left`);
    await new Promise((resolve) => setTimeout(resolve, backoff));
    return fetchWithRetry(url, options, retries - 1, backoff * 2);
  }
}

export async function POST(request: Request) {
  try {
    const { url } = await request.json();

    if (!url) {
      return NextResponse.json({ error: "URL is required" }, { status: 400 });
    }

    console.log(`Fetching subtitles for URL: ${url}`);
    console.log(`Using API URL: ${API_URL}`);

    // 调用 Python API 服务，使用重试机制
    const response = await fetchWithRetry(
      `${API_URL}/video-captions`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      },
      3,
      500
    );

    if (!response.ok) {
      let errorMessage = `Failed to generate subtitle: ${response.status} ${response.statusText}`;
      let errorData = null;

      try {
        errorData = await response.json();
        console.error("API Error Details:", errorData);
        if (errorData.detail) {
          errorMessage = `Error: ${errorData.detail}`;
        }
      } catch (e) {
        console.error("Failed to parse error response:", e);
      }

      throw new Error(errorMessage);
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
