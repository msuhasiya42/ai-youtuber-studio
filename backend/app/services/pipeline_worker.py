"""
Video Processing Pipeline Worker

Orchestrates the complete video processing pipeline:
1. Download audio from YouTube
2. Transcribe audio using Whisper
3. Index transcript in ChromaDB vector store

This worker manages the end-to-end processing flow and updates video status.
"""

from celery import chain
from celery_worker import app as celery_app
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.models import Video, VideoProcessingStatus
import logging

logger = logging.getLogger(__name__)


def update_video_status(
    video_id: int,
    status: VideoProcessingStatus,
    error: str | None = None
):
    """Update video processing status in database"""
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.processing_status = status
            if error:
                video.processing_error = error
            db.commit()
            logger.info(f"Updated video {video_id} status to {status}")
    except Exception as e:
        logger.error(f"Failed to update video status: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="app.services.pipeline_worker.process_video_pipeline")
def process_video_pipeline(video_id: int, youtube_video_id: str):
    """
    Complete video processing pipeline.
    Downloads audio, transcribes it, and indexes in vector store.

    Args:
        video_id: Database video ID
        youtube_video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')

    Returns:
        dict with processing results
    """
    from app.services.ingest_worker import download_audio
    from app.services.transcribe_worker import transcribe_audio
    from app.services.storage_client import StorageClient
    from app.services.vector_store import VectorStore
    from app.services.llm_provider import get_provider
    from datetime import datetime
    import json

    logger.info(f"Starting video processing pipeline for video {video_id}")

    try:
        # Step 1: Download audio
        update_video_status(video_id, VideoProcessingStatus.AUDIO_DOWNLOADING)
        logger.info(f"Step 1/3: Downloading audio for video {video_id}")

        audio_result = download_audio(youtube_video_id)
        if not audio_result.get("success"):
            error_msg = audio_result.get("error", "Unknown audio download error")
            logger.error(f"Audio download failed for video {video_id}: {error_msg}")
            update_video_status(video_id, VideoProcessingStatus.ERROR, error_msg)
            return {"success": False, "error": error_msg, "step": "audio_download"}

        audio_s3_key = audio_result["s3_key"]
        logger.info(f"Audio downloaded successfully: {audio_s3_key}")

        # Update video with audio_s3_key
        db = SessionLocal()
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.audio_s3_key = audio_s3_key
            video.processing_status = VideoProcessingStatus.AUDIO_DOWNLOADED
            db.commit()
        db.close()

        # Step 2: Transcribe audio
        update_video_status(video_id, VideoProcessingStatus.TRANSCRIBING)
        logger.info(f"Step 2/3: Transcribing audio for video {video_id}")

        transcribe_result = transcribe_audio(audio_s3_key, youtube_video_id)
        if not transcribe_result.get("success"):
            error_msg = transcribe_result.get("error", "Unknown transcription error")
            logger.error(f"Transcription failed for video {video_id}: {error_msg}")
            update_video_status(video_id, VideoProcessingStatus.ERROR, error_msg)
            return {"success": False, "error": error_msg, "step": "transcription"}

        transcript_s3_key = transcribe_result["transcript_s3_key"]
        logger.info(f"Transcription completed successfully: {transcript_s3_key}")

        # Update video with transcript_s3_key
        db = SessionLocal()
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.transcript_s3_key = transcript_s3_key
            video.processing_status = VideoProcessingStatus.TRANSCRIBED
            db.commit()
        db.close()

        # Step 3: Index in vector store
        update_video_status(video_id, VideoProcessingStatus.INDEXING)
        logger.info(f"Step 3/3: Indexing transcript for video {video_id}")

        # Fetch transcript from storage
        storage = StorageClient()
        transcript_json = storage.get_object(transcript_s3_key)
        transcript_data = json.loads(transcript_json)

        # Get video details for metadata
        db = SessionLocal()
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise Exception(f"Video {video_id} not found in database")

        metadata = {
            "video_id": video.id,
            "youtube_video_id": video.youtube_video_id,
            "title": video.title,
            "duration_seconds": video.duration_seconds,
            "published_at": video.published_at.isoformat() if video.published_at else None,
        }

        # Index in ChromaDB
        llm_provider = get_provider()
        vector_store = VectorStore(llm_provider)

        chunks_indexed = vector_store.index_transcript(
            video_id=str(video.id),
            youtube_video_id=video.youtube_video_id,
            transcript_data=transcript_data,
            metadata=metadata
        )

        logger.info(f"Successfully indexed {chunks_indexed} chunks for video {video_id}")

        # Mark as complete
        video.processing_status = VideoProcessingStatus.COMPLETE
        video.indexed_at = datetime.utcnow()
        db.commit()
        db.close()

        return {
            "success": True,
            "video_id": video_id,
            "audio_s3_key": audio_s3_key,
            "transcript_s3_key": transcript_s3_key,
            "chunks_indexed": chunks_indexed
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Pipeline failed for video {video_id}: {error_msg}")
        update_video_status(video_id, VideoProcessingStatus.ERROR, error_msg)
        return {"success": False, "error": error_msg, "step": "unknown"}


@celery_app.task(name="app.services.pipeline_worker.queue_video_processing")
def queue_video_processing(video_id: int, youtube_video_id: str):
    """
    Queue a video for processing.
    This is a lightweight task that queues the heavy processing pipeline.

    Args:
        video_id: Database video ID
        youtube_video_id: YouTube video ID
    """
    logger.info(f"Queueing video {video_id} ({youtube_video_id}) for processing")
    process_video_pipeline.delay(video_id, youtube_video_id)
    return {"success": True, "video_id": video_id, "status": "queued"}
