"""
API endpoints for video transcription management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.models import Video, User, Channel
from app.services.ingest_worker import download_audio
from app.services.transcribe_worker import transcribe_audio
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
    Start transcription process for a video.
    Downloads audio (if not already downloaded) and triggers Whisper transcription.
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

    # Step 1: Download audio if not already done
    if not video.audio_s3_key:
        audio_task = download_audio.delay(video.youtube_video_id)
        audio_result = audio_task.get(timeout=300)  # 5 min timeout

        if audio_result["status"] != "success":
            raise HTTPException(status_code=500, detail=f"Audio download failed: {audio_result.get('error')}")

        # Update video with audio S3 key
        video.audio_s3_key = audio_result["s3_key"]
        db.add(video)
        db.commit()

    # Step 2: Transcribe audio
    transcribe_task = transcribe_audio.delay(video.audio_s3_key, video.youtube_video_id)
    transcribe_result = transcribe_task.get(timeout=600)  # 10 min timeout

    if transcribe_result["status"] != "success":
        raise HTTPException(status_code=500, detail=f"Transcription failed: {transcribe_result.get('error')}")

    # Update video with transcript S3 key
    video.transcript_s3_key = transcribe_result["transcript_s3_key"]
    db.add(video)
    db.commit()

    return {
        "status": "success",
        "transcript_s3_key": transcribe_result["transcript_s3_key"],
        "language": transcribe_result.get("language"),
        "duration": transcribe_result.get("duration"),
        "message": "Transcription completed successfully"
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
    Start transcription process asynchronously (non-blocking).
    Returns immediately with task IDs for status checking.
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

    # Start audio download task
    audio_task = download_audio.delay(video.youtube_video_id)

    return {
        "status": "started",
        "audio_task_id": audio_task.id,
        "message": "Transcription process started. Use task ID to check status."
    }
