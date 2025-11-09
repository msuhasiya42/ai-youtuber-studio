"""
Video Processing Pipeline Worker

Orchestrates the complete video processing pipeline:
1. Fetch captions from YouTube
2. Index transcript in ChromaDB vector store

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
    Fetches captions (no audio download) and indexes in vector store.

    Args:
        video_id: Database video ID
        youtube_video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')

    Returns:
        dict with processing results
    """
    from app.services.ingest_worker import fetch_video_captions
    from app.services.storage_client import StorageClient
    from app.services.vector_store import get_vector_store
    from datetime import datetime
    import json

    logger.info(f"Starting video processing pipeline for video {video_id}")

    try:
        # Step 1: Fetch captions (treat as transcription step)
        update_video_status(video_id, VideoProcessingStatus.TRANSCRIBING)
        logger.info(f"Step 1/2: Fetching captions for video {video_id}")

        captions_result = fetch_video_captions(youtube_video_id, db_video_id=video_id)
        if not captions_result.get("success"):
            error_msg = captions_result.get("error", "No captions available or caption fetch error")
            logger.error(f"Caption fetch failed for video {video_id}: {error_msg}")
            update_video_status(video_id, VideoProcessingStatus.ERROR, error_msg)
            return {"success": False, "error": error_msg, "step": "caption_fetch"}

        transcript_s3_key = captions_result["transcript_s3_key"]
        logger.info(f"Captions fetched successfully: {transcript_s3_key}")

        # Update video with transcript_s3_key
        db = SessionLocal()
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.transcript_s3_key = transcript_s3_key
            video.processing_status = VideoProcessingStatus.TRANSCRIBED
            db.commit()
        db.close()

        # Step 2: Index in vector store
        update_video_status(video_id, VideoProcessingStatus.INDEXING)
        logger.info(f"Step 2/2: Indexing transcript for video {video_id}")

        # Fetch transcript from storage
        storage = StorageClient()
        transcript_json_bytes = storage.get_object(transcript_s3_key)
        transcript_data = json.loads(transcript_json_bytes.decode('utf-8'))

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
        vector_store = get_vector_store()

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
