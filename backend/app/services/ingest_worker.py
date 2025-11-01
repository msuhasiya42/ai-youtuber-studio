"""
Ingest worker for downloading audio from YouTube videos using yt-dlp.
"""
from celery_worker import app as celery_app
import yt_dlp
import os
import tempfile
from app.services.storage_client import get_storage_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@celery_app.task
def download_audio(video_id: str) -> dict:
    """
    Download audio from a YouTube video and upload to MinIO storage.

    Args:
        video_id: YouTube video ID (not full URL)

    Returns:
        dict with status and s3_key
    """
    logger.info(f"Starting audio download for video: {video_id}")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    storage_client = get_storage_client()

    # Create temporary directory for download
    with tempfile.TemporaryDirectory() as temp_dir:
        output_template = os.path.join(temp_dir, f"{video_id}.%(ext)s")
        logger.debug(f"Temporary directory created: {temp_dir}")

        # yt-dlp options for audio extraction
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }

        try:
            # Download audio
            logger.info(f"Downloading audio from YouTube: {video_url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                duration = info.get('duration', 0)
                logger.info(f"Audio downloaded successfully (duration: {duration}s)")

            # Find the downloaded file (should be .mp3 after postprocessing)
            audio_file_path = os.path.join(temp_dir, f"{video_id}.mp3")

            if not os.path.exists(audio_file_path):
                logger.warning(f"Expected audio file not found at {audio_file_path}, searching for alternatives")
                # Fallback: check for other extensions
                for file in os.listdir(temp_dir):
                    if file.startswith(video_id):
                        audio_file_path = os.path.join(temp_dir, file)
                        logger.info(f"Found alternative audio file: {file}")
                        break

            if not os.path.exists(audio_file_path):
                error_msg = f"Downloaded audio file not found for {video_id}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            # Get file size for logging
            file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
            logger.info(f"Audio file ready for upload: {file_size_mb:.2f} MB")

            # Upload to MinIO
            s3_key = f"audio/{video_id}.mp3"
            logger.info(f"Uploading audio to storage: {s3_key}")
            storage_client.upload_file(
                file_path=audio_file_path,
                object_name=s3_key,
                content_type="audio/mpeg"
            )
            logger.info(f"Audio upload completed successfully: {s3_key}")

            return {
                "success": True,
                "status": "success",
                "s3_key": s3_key,
                "video_id": video_id,
                "file_size_mb": round(file_size_mb, 2)
            }

        except Exception as e:
            logger.error(f"Error downloading audio for {video_id}: {e}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "error": str(e),
                "video_id": video_id
            }


