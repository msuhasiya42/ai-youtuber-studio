"""
Transcription worker using OpenAI Whisper API for speech-to-text.
"""
from celery_worker import app as celery_app
import os
import tempfile
from openai import OpenAI
from app.services.storage_client import get_storage_client
import json


@celery_app.task
def transcribe_audio(s3_key: str, video_id: str) -> dict:
    """
    Transcribe audio file using OpenAI Whisper API.

    Args:
        s3_key: S3 key of the audio file in MinIO
        video_id: YouTube video ID

    Returns:
        dict with status, transcript_s3_key, and transcript data
    """
    storage_client = get_storage_client()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        # Download audio from MinIO to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            audio_data = storage_client.get_object(s3_key)
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name

        try:
            # Transcribe using Whisper API
            with open(temp_audio_path, "rb") as audio_file:
                transcript_response = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",  # Get timestamps
                    timestamp_granularities=["segment"]  # Get segment-level timestamps
                )

            # Extract transcript data
            transcript_data = {
                "text": transcript_response.text,
                "language": transcript_response.language,
                "duration": transcript_response.duration,
                "segments": []
            }

            # Add segments with timestamps
            if hasattr(transcript_response, 'segments') and transcript_response.segments:
                for segment in transcript_response.segments:
                    transcript_data["segments"].append({
                        "start": segment.get("start"),
                        "end": segment.get("end"),
                        "text": segment.get("text"),
                    })

            # Upload transcript to MinIO
            transcript_s3_key = f"transcripts/{video_id}.json"
            storage_client.upload_bytes(
                data=json.dumps(transcript_data, indent=2).encode('utf-8'),
                object_name=transcript_s3_key,
                content_type="application/json"
            )

            return {
                "status": "success",
                "transcript_s3_key": transcript_s3_key,
                "video_id": video_id,
                "transcript_text": transcript_data["text"],
                "language": transcript_data["language"],
                "duration": transcript_data["duration"],
                "segments_count": len(transcript_data["segments"])
            }

        finally:
            # Clean up temp file
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)

    except Exception as e:
        print(f"Error transcribing audio for {video_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "video_id": video_id
        }


