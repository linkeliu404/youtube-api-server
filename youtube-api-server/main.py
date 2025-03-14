import json
import os
import sys
import traceback
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import urlopen, Request
from typing import Optional, List
import time
import re

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

# 检查是否在 Vercel 环境中运行
IS_VERCEL = os.environ.get('VERCEL') == '1'
print(f"Running in Vercel environment: {IS_VERCEL}", file=sys.stderr)

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
            # 尝试多种方法提取视频ID
            # 方法1: 使用 urlparse
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
            
            # 方法2: 使用正则表达式
            youtube_regex = (
                r'(https?://)?(www\.)?'
                '(youtube|youtu|youtube-nocookie)\.(com|be)/'
                '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
            )
            youtube_regex_match = re.match(youtube_regex, url)
            if youtube_regex_match:
                return youtube_regex_match.group(6)
            
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
            
            print(f"Extracted video ID for data: {video_id}", file=sys.stderr)
        except Exception as e:
            print(f"Error getting video ID: {str(e)}", file=sys.stderr)
            raise HTTPException(status_code=400, detail=f"Error getting video ID from URL: {str(e)}")

        try:
            # 方法1: 使用 YouTube oembed API
            try:
                params = {"format": "json", "url": f"https://www.youtube.com/watch?v={video_id}"}
                oembed_url = "https://www.youtube.com/oembed"
                query_string = urlencode(params)
                full_url = oembed_url + "?" + query_string

                print(f"Fetching video data from: {full_url}", file=sys.stderr)
                start_time = time.time()
                
                # 添加 User-Agent 头，避免被阻止
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                req = Request(full_url, headers=headers)
                
                with urlopen(req) as response:
                    response_text = response.read()
                    video_data = json.loads(response_text.decode())
                    
                    end_time = time.time()
                    print(f"Video data fetched in {end_time - start_time:.2f} seconds", file=sys.stderr)
                    
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
                print(f"Error getting video data from oembed API: {str(e)}", file=sys.stderr)
                # 如果 oembed API 失败，返回简单的数据
                return {
                    "title": f"YouTube Video ({video_id})",
                    "author_name": "Unknown",
                    "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/0.jpg",
                }
        except Exception as e:
            print(f"Error getting video data: {str(e)}", file=sys.stderr)
            # 返回最基本的数据，避免整个请求失败
            return {
                "title": f"YouTube Video ({video_id})",
                "author_name": "Unknown",
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/0.jpg",
            }

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
            title = video_data.get("title", f"YouTube Video ({video_id})")
            print(f"Video title: {title}", file=sys.stderr)

            # 获取字幕
            print(f"Getting captions for video ID: {video_id}", file=sys.stderr)
            captions = None
            error_messages = []
            
            # 尝试直接获取字幕，不使用复杂的重试逻辑
            try:
                start_time = time.time()
                
                # 如果指定了语言，使用指定语言
                if languages and len(languages) > 0:
                    print(f"Using languages: {languages}", file=sys.stderr)
                    captions = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
                else:
                    # 否则尝试获取默认语言
                    print("No language specified, using default", file=sys.stderr)
                    captions = YouTubeTranscriptApi.get_transcript(video_id)
                
                end_time = time.time()
                print(f"Successfully retrieved captions in {end_time - start_time:.2f} seconds", file=sys.stderr)
            except Exception as e:
                error_message = f"Failed to get captions: {str(e)}"
                print(error_message, file=sys.stderr)
                error_messages.append(error_message)
                
                # 如果失败，尝试列出可用语言并使用第一个
                try:
                    print("Trying to list available languages...", file=sys.stderr)
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    available_languages = [t.language_code for t in transcript_list]
                    print(f"Available languages: {available_languages}", file=sys.stderr)
                    
                    if available_languages:
                        first_lang = available_languages[0]
                        print(f"Trying with first available language: {first_lang}", file=sys.stderr)
                        captions = YouTubeTranscriptApi.get_transcript(video_id, languages=[first_lang])
                        print(f"Successfully retrieved captions with language {first_lang}", file=sys.stderr)
                except Exception as inner_e:
                    error_message = f"Failed to list available languages: {str(inner_e)}"
                    print(error_message, file=sys.stderr)
                    error_messages.append(error_message)
                    
                    # 如果仍然失败，尝试使用 en 语言
                    try:
                        print("Trying with 'en' language...", file=sys.stderr)
                        captions = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                        print("Successfully retrieved captions with 'en' language", file=sys.stderr)
                    except Exception as en_e:
                        error_message = f"Failed to get captions with 'en' language: {str(en_e)}"
                        print(error_message, file=sys.stderr)
                        error_messages.append(error_message)
            
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
            # 如果没有找到字幕，返回错误信息
            error_detail = "No captions found for this video"
            if error_messages:
                error_detail += f". Errors: {'; '.join(error_messages)}"
            
            raise HTTPException(status_code=404, detail=error_detail)
        except HTTPException:
            # 重新抛出 HTTPException
            raise
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
            
            print(f"Extracted video ID for timestamps: {video_id}", file=sys.stderr)
        except Exception as e:
            print(f"Error getting video ID for timestamps: {str(e)}", file=sys.stderr)
            raise HTTPException(status_code=400, detail=f"Error getting video ID from URL: {str(e)}")

        try:
            print(f"Getting timestamps for video ID: {video_id}", file=sys.stderr)
            start_time = time.time()
            
            # 尝试使用指定语言或默认语言
            try:
                if languages and len(languages) > 0:
                    captions = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
                else:
                    captions = YouTubeTranscriptApi.get_transcript(video_id)
            except Exception as e:
                print(f"Failed to get captions for timestamps: {str(e)}", file=sys.stderr)
                # 尝试使用 en 语言
                captions = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            
            end_time = time.time()
            print(f"Retrieved captions for timestamps in {end_time - start_time:.2f} seconds", file=sys.stderr)
            
            timestamps = []
            for line in captions:
                start = int(line["start"])
                minutes, seconds = divmod(start, 60)
                timestamps.append(f"{minutes}:{seconds:02d} - {line['text']}")
            return timestamps
        except Exception as e:
            print(f"Error generating timestamps: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise HTTPException(status_code=500, detail=f"Error generating timestamps: {str(e)}")

class YouTubeRequest(BaseModel):
    url: str
    languages: Optional[List[str]] = None

@app.post("/video-data")
async def get_video_data(request: YouTubeRequest):
    """Endpoint to get video metadata"""
    print(f"Received request for video data: {request.url}", file=sys.stderr)
    return YouTubeTools.get_video_data(request.url)

@app.post("/video-captions")
async def get_video_captions(request: YouTubeRequest):
    """Endpoint to get video captions"""
    print(f"Received request for video captions: {request.url}, languages: {request.languages}", file=sys.stderr)
    return YouTubeTools.get_video_captions(request.url, request.languages)

@app.post("/video-timestamps")
async def get_video_timestamps(request: YouTubeRequest):
    """Endpoint to get video timestamps"""
    print(f"Received request for video timestamps: {request.url}, languages: {request.languages}", file=sys.stderr)
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