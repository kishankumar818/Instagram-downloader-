# Instagram Media API

A Python API for fetching media URLs from supported public Instagram posts.

## Features

- Public Instagram post URL support
- Reel URL support
- Image URL retrieval
- Video URL retrieval
- Multiple items from carousel posts
- Optional API key
- CORS support
- Deployable to Vercel

## Important limitations

- Instagram may require login, block cloud IPs, or rate-limit requests.
- Private or restricted content is not supported.
- This project uses an unofficial extraction library and may break when
  Instagram changes its website.
- Media URLs can expire.
- Only the source quality returned by Instagram is exposed.
- Audio is not returned as a separate MP3 by the API.
- Use this only for content you own or have permission to download.

## Run locally

### 1. Create a virtual environment

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install packages

```bash
pip install -r requirements.txt
```

### 3. Start the API

```bash
python api/index.py
```

API runs at:

```text
http://127.0.0.1:5000
```

## Health check

```bash
curl http://127.0.0.1:5000/api/health
```

Expected response:

```json
{
  "success": true,
  "status": "ok"
}
```

## Fetch media

```bash
curl -X POST "http://127.0.0.1:5000/api/media" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.instagram.com/reel/SHORTCODE/"}'
```

Replace `SHORTCODE` with a real public post shortcode.

Example response shape:

```json
{
  "success": true,
  "data": {
    "shortcode": "SHORTCODE",
    "post_url": "https://www.instagram.com/p/SHORTCODE/",
    "caption": "Example caption",
    "media_count": 1,
    "media": [
      {
        "position": 1,
        "type": "video",
        "thumbnail_url": "https://...",
        "download_url": "https://...",
        "quality": "source",
        "available_qualities": ["source"],
        "audio_note": "This is the video URL. Extract audio separately with FFmpeg."
      }
    ],
    "notes": [
      "Media URLs may expire.",
      "Only source quality returned by Instagram is listed.",
      "Public access depends on Instagram availability and restrictions."
    ]
  }
}
```

## Download video

Take the `download_url` from the response:

```bash
curl -L "PASTE_DOWNLOAD_URL_HERE" -o video.mp4
```

The URL may expire or be blocked depending on Instagram's restrictions.

## Extract MP3 audio

Install FFmpeg on your computer or processing server, then:

```bash
ffmpeg -i video.mp4 -vn -codec:a libmp3lame -q:a 2 audio.mp3
```

This works only when the video has an audio track and your FFmpeg build
includes `libmp3lame`.

## Optional API key

Set the `API_KEY` environment variable on the server.

Example request:

```bash
curl -X POST "https://YOUR-PROJECT.vercel.app/api/media" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"url":"https://www.instagram.com/reel/SHORTCODE/"}'
```

If `API_KEY` is not set, the endpoint is public.

Do not embed a secret API key in a browser frontend or mobile app.
For those clients, call your own backend, which can keep the key private.

## CORS

By default, the API allows requests from any origin.

To restrict browser access, set `ALLOWED_ORIGIN`:

```text
https://your-frontend-domain.com
```

CORS is not authentication. Non-browser clients can still call the API,
so use proper authentication and rate limiting where needed.

## Deploy to Vercel

1. Push the project to a GitHub repository.
2. Log in to Vercel and choose **Add New → Project**.
3. Import the repository.
4. Optionally add environment variables:
   - `API_KEY`
   - `ALLOWED_ORIGIN`
5. Deploy.
6. Test:

```text
https://YOUR-PROJECT.vercel.app/api/health
```

Then call `/api/media` with a POST request.

A successful health check confirms the API is running; it does not
guarantee Instagram requests will succeed from Vercel's servers.