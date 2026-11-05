import os
import re
from urllib.parse import urlparse

import instaloader
from flask import Flask, jsonify, request

app = Flask(__name__)

# Allowed Instagram post types:
# /p/SHORTCODE/
# /reel/SHORTCODE/
# /tv/SHORTCODE/
POST_PATH_PATTERN = re.compile(
    r"^/(p|reel|tv)/([A-Za-z0-9_-]+)/?$"
)

ALLOWED_HOSTS = {
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
}


def json_error(message, status_code, code=None):
    body = {
        "success": False,
        "error": {
            "message": message,
        },
    }

    if code:
        body["error"]["code"] = code

    return jsonify(body), status_code


@app.after_request
def add_cors_headers(response):
    """
    By default, API can be called from any website.

    Set ALLOWED_ORIGIN in Vercel for a specific frontend, e.g.
    https://example.com
    """
    allowed_origin = os.getenv("ALLOWED_ORIGIN", "*")

    response.headers["Access-Control-Allow-Origin"] = allowed_origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, X-API-Key"
    )
    response.headers["Cache-Control"] = "no-store"

    return response


def check_api_key():
    """
    Optional API-key protection.

    If API_KEY is not set, the API is public.
    If API_KEY is set, callers must send X-API-Key.
    """
    expected_key = os.getenv("API_KEY")

    if not expected_key:
        return True

    supplied_key = request.headers.get("X-API-Key", "")
    return supplied_key == expected_key


def extract_shortcode(instagram_url):
    if not isinstance(instagram_url, str):
        raise ValueError("URL must be a string.")

    instagram_url = instagram_url.strip()

    if len(instagram_url) > 2048:
        raise ValueError("URL is too long.")

    parsed = urlparse(instagram_url)

    if parsed.scheme not in ("https", "http"):
        raise ValueError("URL must begin with http:// or https://.")

    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only instagram.com URLs are supported.")

    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Invalid Instagram URL.")

    match = POST_PATH_PATTERN.fullmatch(parsed.path)

    if not match:
        raise ValueError(
            "Use a valid Instagram post, reel, or IGTV URL."
        )

    return match.group(2)


def build_media_item(node, position):
    is_video = bool(node.is_video)

    item = {
        "position": position,
        "type": "video" if is_video else "image",
        "thumbnail_url": node.url,
    }

    if is_video:
        item["download_url"] = node.video_url
        item["quality"] = "source"
        item["available_qualities"] = ["source"]
        item["audio_note"] = (
            "This is the video URL. Extract audio separately with FFmpeg."
        )
    else:
        item["download_url"] = node.url
        item["quality"] = "source"

    return item


def fetch_post(shortcode):
    # No Instagram login credentials or cookies required.
    # Private and login-restricted content is not supported.
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
        request_timeout=15,
        max_connection_attempts=1,
    )

    post = instaloader.Post.from_shortcode(loader.context, shortcode)

    media = []

    if post.typename == "GraphSidecar":
        for position, node in enumerate(post.get_sidecar_nodes(), start=1):
            media.append(build_media_item(node, position))
    else:
        media.append(build_media_item(post, 1))

    return {
        "shortcode": shortcode,
        "post_url": f"https://www.instagram.com/p/{shortcode}/",
        "caption": post.caption,
        "media_count": len(media),
        "media": media,
        "notes": [
            "Media URLs may expire.",
            "Only source quality returned by Instagram is listed.",
            "Public access depends on Instagram availability and restrictions.",
        ],
    }


@app.route("/", methods=["GET"])
def home():
    return jsonify(
        {
            "success": True,
            "name": "Instagram Media API",
            "endpoints": {
                "health": "GET /api/health",
                "media": "POST /api/media",
            },
        }
    )


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "success": True,
            "status": "ok",
        }
    )


@app.route("/api/media", methods=["POST", "OPTIONS"])
def media():
    if request.method == "OPTIONS":
        return "", 204

    if not check_api_key():
        return json_error(
            "Invalid or missing API key.",
            401,
            "UNAUTHORIZED",
        )

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return json_error(
            "Send a JSON object with a 'url' field.",
            400,
            "INVALID_JSON",
        )

    try:
        shortcode = extract_shortcode(payload.get("url"))
    except (ValueError, TypeError) as exc:
        return json_error(str(exc), 400, "INVALID_URL")

    try:
        result = fetch_post(shortcode)

        return jsonify(
            {
                "success": True,
                "data": result,
            }
        )

    except instaloader.exceptions.ProfileNotExistsException:
        return json_error(
            "Post not found or unavailable.",
            404,
            "NOT_FOUND",
        )

    except instaloader.exceptions.LoginRequiredException:
        return json_error(
            "Instagram requires login for this content or request.",
            403,
            "LOGIN_REQUIRED",
        )

    except instaloader.exceptions.ConnectionException:
        return json_error(
            "Could not fetch the post. Instagram may be blocking or "
            "rate-limiting this server.",
            502,
            "INSTAGRAM_UNAVAILABLE",
        )

    except instaloader.exceptions.InstaloaderException:
        return json_error(
            "Could not access this post. It may be private, deleted, "
            "restricted, or temporarily unavailable.",
            502,
            "FETCH_FAILED",
        )

    except Exception:
        # Do not return internal error details or environment secrets.
        app.logger.exception("Unexpected error while fetching Instagram post")

        return json_error(
            "An unexpected error occurred.",
            500,
            "INTERNAL_ERROR",
        )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
