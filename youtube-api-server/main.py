import json
import os
import sys
import traceback
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import urlopen
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    raise ImportError(
        "`youtube_transcript_api` not installed. Please install using `pip install youtube_transcript_api`"
    )

app = FastAPI(title="YouTube Tools API")

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境中应该限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_detail = {
        "error": str(exc),
        "traceback": traceback.format_exc()
    }
    print(f"Global exception: {error_detail}", file=sys.stderr)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"}
    )

class YouTubeTools:
    @staticmethod
    def get_youtube_video_id(url: str) -> Optional[str]:
        """Function to get the video ID from a YouTube URL."""
        try:
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname

            if hostname == "youtu.be":
                return parsed_url.path[1:]
            if hostname in ("www.youtube.com", "youtube.com"):
                if parsed_url.path == "/watch":
                    query_params = parse_qs(parsed_url.query)
                    return query_params.get("v", [None])[0]
                if parsed_url.path.startswith("/embed/"):
                    return parsed_url.path.split("/")[2]
                if parsed_url.path.startswith("/v/"):
                    return parsed_url.path.split("/")[2]
            return None
        except Exception as e:
            print(f"Error parsing YouTube URL: {url}, Error: {str(e)}", file=sys.stderr)
            return None

    @staticmethod
    def get_video_data(url: str) -> dict:
        """Function to get video data from a YouTube URL."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        except Exception as e:
            print(f"Error getting video ID: {str(e)}", file=sys.stderr)
            raise HTTPException(status_code=400, detail=f"Error getting video ID from URL: {str(e)}")

        try:
            params = {"format": "json", "url": f"https://www.youtube.com/watch?v={video_id}"}
            oembed_url = "https://www.youtube.com/oembed"
            query_string = urlencode(params)
            full_url = oembed_url + "?" + query_string

            with urlopen(full_url) as response:
                response_text = response.read()
                video_data = json.loads(response_text.decode())
                clean_data = {
                    "title": video_data.get("title"),
                    "author_name": video_data.get("author_name"),
                    "author_url": video_data.get("author_url"),
                    "type": video_data.get("type"),
                    "height": video_data.get("height"),
                    "width": video_data.get("width"),
                    "version": video_data.get("version"),
                    "provider_name": video_data.get("provider_name"),
                    "provider_url": video_data.get("provider_url"),
                    "thumbnail_url": video_data.get("thumbnail_url"),
                }
                return clean_data
        except Exception as e:
            print(f"Error getting video data: {str(e)}", file=sys.stderr)
            raise HTTPException(status_code=500, detail=f"Error getting video data: {str(e)}")

    @staticmethod
    def get_video_captions(url: str, languages: Optional[List[str]] = None) -> dict:
        """Get captions from a YouTube video."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
            
            print(f"Extracted video ID: {video_id}", file=sys.stderr)
        except Exception as e:
            print(f"Error getting video ID: {str(e)}", file=sys.stderr)
            raise HTTPException(status_code=400, detail=f"Error getting video ID from URL: {str(e)}")

        try:
            # 获取视频标题
            print(f"Getting video data for ID: {video_id}", file=sys.stderr)
            video_data = YouTubeTools.get_video_data(url)
            title = video_data.get("title", "")
            print(f"Video title: {title}", file=sys.stderr)

            # 获取字幕
            print(f"Getting captions for video ID: {video_id}", file=sys.stderr)
            captions = None
            
            try:
                # 首先尝试使用指定语言获取字幕
                if languages:
                    print(f"Using languages: {languages}", file=sys.stderr)
                    try:
                        captions = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
                        print(f"Successfully retrieved captions with specified languages", file=sys.stderr)
                    except Exception as e:
                        print(f"Failed to get captions with specified languages: {str(e)}", file=sys.stderr)
                        # 如果指定语言失败，尝试获取所有可用语言
                        print("Trying to list available languages...", file=sys.stderr)
                        try:
                            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                            available_languages = [t.language_code for t in transcript_list]
                            print(f"Available languages: {available_languages}", file=sys.stderr)
                            
                            # 尝试使用第一个可用语言
                            if available_languages:
                                print(f"Trying with first available language: {available_languages[0]}", file=sys.stderr)
                                captions = YouTubeTranscriptApi.get_transcript(video_id, languages=[available_languages[0]])
                        except Exception as inner_e:
                            print(f"Failed to list available languages: {str(inner_e)}", file=sys.stderr)
                else:
                    # 尝试使用默认语言（通常是视频的原始语言）
                    print("No language specified, using default", file=sys.stderr)
                    try:
                        captions = YouTubeTranscriptApi.get_transcript(video_id)
                        print("Successfully retrieved captions with default language", file=sys.stderr)
                    except Exception as e:
                        print(f"Failed to get captions with default language: {str(e)}", file=sys.stderr)
                        # 尝试列出所有可用语言并使用第一个
                        print("Trying to list available languages...", file=sys.stderr)
                        try:
                            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                            available_languages = [t.language_code for t in transcript_list]
                            print(f"Available languages: {available_languages}", file=sys.stderr)
                            
                            # 尝试使用第一个可用语言
                            if available_languages:
                                print(f"Trying with first available language: {available_languages[0]}", file=sys.stderr)
                                captions = YouTubeTranscriptApi.get_transcript(video_id, languages=[available_languages[0]])
                        except Exception as inner_e:
                            print(f"Failed to list available languages: {str(inner_e)}", file=sys.stderr)
                            raise HTTPException(
                                status_code=500, 
                                detail=f"Could not retrieve subtitles. Error: {str(e)}. Inner error: {str(inner_e)}"
                            )
            except Exception as e:
                print(f"All attempts to get captions failed: {str(e)}", file=sys.stderr)
                raise HTTPException(
                    status_code=500, 
                    detail=f"All attempts to get captions failed: {str(e)}"
                )
            
            if captions:
                print(f"Successfully retrieved {len(captions)} caption items", file=sys.stderr)
                # 格式化时间戳
                formatted_captions = []
                for caption in captions:
                    start = int(caption["start"])
                    minutes, seconds = divmod(start, 60)
                    formatted_caption = {
                        "text": caption["text"],
                        "timestamp": f"{minutes}:{seconds:02d}",
                        "start": start,
                        "duration": caption["duration"]
                    }
                    formatted_captions.append(formatted_caption)
                return {
                    "title": title,
                    "subtitles": formatted_captions
                }
            
            print("No captions found", file=sys.stderr)
            return {
                "title": title,
                "subtitles": []
            }
        except Exception as e:
            print(f"Error getting captions: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise HTTPException(status_code=500, detail=f"Error getting captions for video: {str(e)}")

    @staticmethod
    def get_video_timestamps(url: str, languages: Optional[List[str]] = None) -> List[str]:
        """Generate timestamps for a YouTube video based on captions."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        except Exception:
            raise HTTPException(status_code=400, detail="Error getting video ID from URL")

        try:
            captions = YouTubeTranscriptApi.get_transcript(video_id, languages=languages or ["en"])
            timestamps = []
            for line in captions:
                start = int(line["start"])
                minutes, seconds = divmod(start, 60)
                timestamps.append(f"{minutes}:{seconds:02d} - {line['text']}")
            return timestamps
        except Exception as e:
            print(f"Error generating timestamps: {str(e)}", file=sys.stderr)
            raise HTTPException(status_code=500, detail=f"Error generating timestamps: {str(e)}")

class YouTubeRequest(BaseModel):
    url: str
    languages: Optional[List[str]] = None

@app.post("/video-data")
async def get_video_data(request: YouTubeRequest):
    """Endpoint to get video metadata"""
    return YouTubeTools.get_video_data(request.url)

@app.post("/video-captions")
async def get_video_captions(request: YouTubeRequest):
    """Endpoint to get video captions"""
    return YouTubeTools.get_video_captions(request.url, request.languages)

@app.post("/video-timestamps")
async def get_video_timestamps(request: YouTubeRequest):
    """Endpoint to get video timestamps"""
    return YouTubeTools.get_video_timestamps(request.url, request.languages)

# 添加健康检查端点
@app.get("/")
async def root():
    return {"status": "ok", "message": "YouTube Subtitle API is running"}

if __name__ == "__main__":
    # Use environment variable for port, default to 8000 if not set
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)