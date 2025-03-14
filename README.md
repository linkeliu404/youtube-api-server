# YouTube Subtitle Generator

一个简单的 YouTube 字幕生成器，可以从 YouTube 视频中提取字幕并下载为 SRT 格式。

## 项目结构

- `youtube-subtitle/`: 前端 Next.js 应用
- `youtube-api-server/`: 后端 FastAPI 应用

## 部署到 Vercel

### 后端部署

1. 在 Vercel 上创建一个新项目
2. 导入 `youtube-api-server` 目录
3. 配置以下设置:
   - Build Command: `pip install -r requirements.txt`
   - Output Directory: `.`
   - Install Command: `pip install -r requirements.txt`
4. 添加环境变量（如果需要）
5. 部署项目

### 前端部署

1. 在 Vercel 上创建一个新项目
2. 导入 `youtube-subtitle` 目录
3. 配置以下环境变量:
   - `NEXT_PUBLIC_API_URL`: 设置为后端 API 的 URL（例如 `https://youtube-api-server.vercel.app`）
4. 部署项目

## 本地开发

### 后端

```bash
cd youtube-api-server
pip install -r requirements.txt
python main.py
```

### 前端

```bash
cd youtube-subtitle
npm install
npm run dev
```

## 功能

- 从 YouTube 视频中提取字幕
- 显示带有时间戳的字幕
- 下载字幕为 SRT 格式
- 支持在新标签页中查看结果
