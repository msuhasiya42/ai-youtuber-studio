"""
API endpoints for video transcript management.
Uses YouTube Caption API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.models import Video, User, Channel
from app.services.ingest_worker import fetch_video_captions
from app.services.storage_client import get_storage_client
from app.api.channels import get_current_user
import json


router = APIRouter()


class TranscribeRequest(BaseModel):
    video_id: int  # Database video ID


@router.post("/videos/{video_id}/transcribe")
async def start_transcription(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch transcript directly from YouTube captions.
    """
    # Get video and verify ownership through channel
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Verify channel belongs to current user
    channel = db.query(Channel).filter(
        Channel.id == video.channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=403, detail="Not authorized to access this video")

    # Check if already transcribed
    if video.transcript_s3_key:
        return {
            "status": "already_transcribed",
            "transcript_s3_key": video.transcript_s3_key,
            "message": "Video already has a transcript"
        }

    # Fetch captions directly from YouTube API
    caption_task = fetch_video_captions.delay(
        video.youtube_video_id, 
        db_video_id=video.id
    )
    caption_result = caption_task.get(timeout=120)  # 2 min timeout

    if caption_result["status"] == "no_captions":
        raise HTTPException(
            status_code=404, 
            detail="No captions available for this video. Please enable captions on YouTube first."
        )

    if caption_result["status"] != "success":
        raise HTTPException(
            status_code=500, 
            detail=f"Caption fetch failed: {caption_result.get('error')}"
        )

    # Video record already updated by worker
    db.refresh(video)

    return {
        "status": "success",
        "transcript_s3_key": caption_result["transcript_s3_key"],
        "language": caption_result.get("language"),
        "track_kind": caption_result.get("track_kind"),
        "segments_count": caption_result.get("segments_count"),
        "message": "Transcript fetched successfully from YouTube captions"
    }


@router.get("/videos/{video_id}/transcript")
async def get_transcript(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get transcript for a video.
    """
    # Get video and verify ownership
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Verify channel belongs to current user
    channel = db.query(Channel).filter(
        Channel.id == video.channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=403, detail="Not authorized to access this video")

    if not video.transcript_s3_key:
        raise HTTPException(status_code=404, detail="Transcript not found. Please transcribe the video first.")

    # Fetch transcript from storage
    storage_client = get_storage_client()

    try:
        transcript_data = storage_client.get_object(video.transcript_s3_key)
        transcript_json = json.loads(transcript_data.decode('utf-8'))

        return {
            "video_id": video.id,
            "youtube_video_id": video.youtube_video_id,
            "title": video.title,
            "transcript": transcript_json
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {e}")


@router.post("/videos/{video_id}/transcribe-async")
async def start_transcription_async(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start caption fetching asynchronously (non-blocking).
    Returns immediately with task ID for status checking.
    """
    # Get video and verify ownership
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Verify channel belongs to current user
    channel = db.query(Channel).filter(
        Channel.id == video.channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=403, detail="Not authorized to access this video")

    # Check if already transcribed
    if video.transcript_s3_key:
        return {
            "status": "already_transcribed",
            "transcript_s3_key": video.transcript_s3_key
        }

    # Start caption fetch task
    caption_task = fetch_video_captions.delay(
        video.youtube_video_id,
        db_video_id=video.id
    )

    return {
        "status": "started",
        "task_id": caption_task.id,
        "message": "Caption fetch started. Use task ID to check status."
    }
