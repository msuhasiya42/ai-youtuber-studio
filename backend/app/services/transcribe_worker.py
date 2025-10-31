from celery_worker import app


@app.task
def transcribe_audio(s3_key: str) -> dict:
    # Placeholder for Whisper
    return {"status": "ok", "transcript_s3_key": s3_key.replace("audio/", "transcripts/").replace(".mp3", ".txt")}


