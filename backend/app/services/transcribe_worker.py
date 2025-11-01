"""
Transcription worker using OpenAI Whisper API for speech-to-text.
"""
from celery_worker import app as celery_app
import os
import tempfile
import time
from openai import OpenAI
from app.services.storage_client import get_storage_client
from app.core.logging_config import get_logger
import json

logger = get_logger(__name__)


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
    logger.info(f"Starting transcription for video: {video_id}, audio: {s3_key}")
    storage_client = get_storage_client()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        # Download audio from MinIO to temp file
        logger.info(f"Downloading audio from storage: {s3_key}")
        start_time = time.time()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            audio_data = storage_client.get_object(s3_key)
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
            file_size_mb = len(audio_data) / (1024 * 1024)

        download_duration = time.time() - start_time
        logger.info(f"Audio downloaded ({file_size_mb:.2f} MB) in {download_duration:.2f}s")

        try:
            # Transcribe using Whisper API
            logger.info(f"Sending audio to OpenAI Whisper API for transcription")
            whisper_start = time.time()
            with open(temp_audio_path, "rb") as audio_file:
                transcript_response = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",  # Get timestamps
                    timestamp_granularities=["segment"]  # Get segment-level timestamps
                )

            whisper_duration = time.time() - whisper_start
            logger.info(
                f"Whisper API completed in {whisper_duration:.2f}s "
                f"(language: {transcript_response.language}, duration: {transcript_response.duration}s)"
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
                logger.debug(f"Processing {len(transcript_response.segments)} transcript segments")
                for segment in transcript_response.segments:
                    transcript_data["segments"].append({
                        "start": segment.get("start"),
                        "end": segment.get("end"),
                        "text": segment.get("text"),
                    })
                logger.info(f"Extracted {len(transcript_data['segments'])} segments from transcript")

            # Upload transcript to MinIO
            transcript_s3_key = f"transcripts/{video_id}.json"
            transcript_json = json.dumps(transcript_data, indent=2).encode('utf-8')
            transcript_size_kb = len(transcript_json) / 1024

            logger.info(f"Uploading transcript to storage: {transcript_s3_key} ({transcript_size_kb:.2f} KB)")
            storage_client.upload_bytes(
                data=transcript_json,
                object_name=transcript_s3_key,
                content_type="application/json"
            )
            logger.info(f"Transcript uploaded successfully: {transcript_s3_key}")

            total_duration = time.time() - start_time
            logger.info(
                f"Transcription complete for {video_id} - "
                f"Total time: {total_duration:.2f}s, "
                f"Text length: {len(transcript_data['text'])} chars, "
                f"Segments: {len(transcript_data['segments'])}"
            )

            return {
                "success": True,
                "status": "success",
                "transcript_s3_key": transcript_s3_key,
                "video_id": video_id,
                "transcript_text": transcript_data["text"],
                "language": transcript_data["language"],
                "duration": transcript_data["duration"],
                "segments_count": len(transcript_data["segments"]),
                "transcription_time_s": round(whisper_duration, 2)
            }

        finally:
            # Clean up temp file
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
                logger.debug(f"Temporary audio file cleaned up: {temp_audio_path}")

    except Exception as e:
        logger.error(f"Error transcribing audio for {video_id}: {e}", exc_info=True)
        return {
            "success": False,
            "status": "error",
            "error": str(e),
            "video_id": video_id
        }


