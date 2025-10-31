from celery_worker import app


@app.task
def download_audio(video_url: str) -> dict:
    # Placeholder for yt-dlp usage
    return {"status": "ok", "s3_key": f"audio/{video_url.split('=')[-1]}.mp3"}


