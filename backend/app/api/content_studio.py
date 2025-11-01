"""
Content Studio API endpoints - AI-powered content creation features.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.db.session import get_db
from app.models.models import User, Channel, Video
from app.api.channels import get_current_user
from app.services.pattern_analyzer import get_pattern_analyzer
from app.services.title_optimizer import get_title_optimizer
from app.services.generation_worker import generate_script_with_rag
from app.services.vector_store import get_vector_store
from app.services.storage_client import get_storage_client
import json


router = APIRouter()


# Request/Response Models
class AnalyzeChannelRequest(BaseModel):
    channel_id: int
    top_n: Optional[int] = 10


class GenerateScriptRequest(BaseModel):
    channel_id: int
    topic: str
    tone: Optional[str] = None
    minutes: Optional[int] = 8
    video_format: Optional[str] = "standard"  # 'standard', 'short', 'tutorial'


class GenerateTitlesRequest(BaseModel):
    channel_id: int
    topic: str
    count: Optional[int] = 5


class IndexVideoRequest(BaseModel):
    video_id: int  # Database video ID


# Endpoints
@router.post("/analyze-patterns")
async def analyze_channel_patterns(
    request: AnalyzeChannelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze performance patterns from top videos.
    """
    # Verify channel belongs to user
    channel = db.query(Channel).filter(
        Channel.id == request.channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found or not authorized")

    # Analyze patterns
    pattern_analyzer = get_pattern_analyzer()
    patterns = pattern_analyzer.analyze_channel_patterns(
        db,
        channel_id=request.channel_id,
        top_n=request.top_n
    )

    return patterns


@router.post("/generate-script")
async def generate_script(
    request: GenerateScriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a video script using RAG and channel insights.
    """
    # Verify channel belongs to user
    channel = db.query(Channel).filter(
        Channel.id == request.channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found or not authorized")

    # Generate script using Celery task
    task = generate_script_with_rag.delay(
        topic=request.topic,
        channel_id=request.channel_id,
        tone=request.tone,
        minutes=request.minutes,
        video_format=request.video_format
    )

    # Get result (with timeout)
    try:
        result = task.get(timeout=60)  # 60 second timeout
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


@router.post("/generate-titles")
async def generate_titles(
    request: GenerateTitlesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate and score title variations for a video topic.
    """
    # Verify channel belongs to user
    channel = db.query(Channel).filter(
        Channel.id == request.channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found or not authorized")

    # Generate titles
    title_optimizer = get_title_optimizer()
    titles = title_optimizer.generate_title_variations(
        topic=request.topic,
        db=db,
        channel_id=request.channel_id,
        count=request.count
    )

    return {
        "topic": request.topic,
        "titles": titles,
        "count": len(titles)
    }


@router.post("/index-video")
async def index_video_transcript(
    request: IndexVideoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Index a video's transcript in the vector store for RAG.
    """
    # Get video and verify ownership
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Verify channel belongs to user
    channel = db.query(Channel).filter(
        Channel.id == video.channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if transcript exists
    if not video.transcript_s3_key:
        raise HTTPException(
            status_code=400,
            detail="Video has no transcript. Please transcribe it first."
        )

    # Fetch transcript from storage
    storage_client = get_storage_client()
    try:
        transcript_data_raw = storage_client.get_object(video.transcript_s3_key)
        transcript_data = json.loads(transcript_data_raw.decode('utf-8'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {e}")

    # Index in vector store
    vector_store = get_vector_store()
    try:
        chunks_count = vector_store.index_transcript(
            video_id=str(video.id),
            youtube_video_id=video.youtube_video_id,
            transcript_data=transcript_data,
            metadata={
                "views": video.views,
                "likes": video.likes,
                "title": video.title,
                "duration": video.duration_seconds
            }
        )

        return {
            "status": "success",
            "video_id": video.id,
            "youtube_video_id": video.youtube_video_id,
            "chunks_indexed": chunks_count,
            "message": "Video transcript indexed successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")


@router.get("/insights/{channel_id}")
async def get_channel_insights(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive insights for a channel.
    Combines pattern analysis with video stats.
    """
    # Verify channel belongs to user
    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found or not authorized")

    # Get basic stats
    total_videos = db.query(Video).filter(Video.channel_id == channel_id).count()
    transcribed_videos = db.query(Video).filter(
        Video.channel_id == channel_id,
        Video.transcript_s3_key.isnot(None)
    ).count()

    # Get pattern analysis
    pattern_analyzer = get_pattern_analyzer()
    patterns = pattern_analyzer.analyze_channel_patterns(db, channel_id, top_n=10)

    # Get vector store stats
    vector_store = get_vector_store()
    vector_stats = vector_store.get_collection_stats()

    return {
        "channel": {
            "id": channel.id,
            "name": channel.name,
            "subscribers": channel.subscribers,
            "total_views": channel.total_views
        },
        "stats": {
            "total_videos": total_videos,
            "transcribed_videos": transcribed_videos,
            "indexed_chunks": vector_stats.get("total_chunks", 0)
        },
        "patterns": patterns,
        "ready_for_ai": transcribed_videos > 0
    }


@router.post("/process-video-pipeline/{video_id}")
async def process_video_pipeline(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run the complete video processing pipeline:
    1. Download audio (if needed)
    2. Transcribe (if needed)
    3. Index in vector store

    This is a convenience endpoint that runs all steps.
    """
    from app.services.ingest_worker import download_audio
    from app.services.transcribe_worker import transcribe_audio

    # Get video and verify ownership
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Verify channel belongs to user
    channel = db.query(Channel).filter(
        Channel.id == video.channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=403, detail="Not authorized")

    pipeline_status = {
        "video_id": video.id,
        "youtube_video_id": video.youtube_video_id,
        "steps": []
    }

    # Step 1: Download audio
    if not video.audio_s3_key:
        try:
            audio_task = download_audio.delay(video.youtube_video_id)
            audio_result = audio_task.get(timeout=300)

            if audio_result["status"] == "success":
                video.audio_s3_key = audio_result["s3_key"]
                db.add(video)
                db.commit()
                pipeline_status["steps"].append({"step": "audio_download", "status": "success"})
            else:
                pipeline_status["steps"].append({"step": "audio_download", "status": "failed", "error": audio_result.get("error")})
                return pipeline_status
        except Exception as e:
            pipeline_status["steps"].append({"step": "audio_download", "status": "failed", "error": str(e)})
            return pipeline_status
    else:
        pipeline_status["steps"].append({"step": "audio_download", "status": "skipped", "reason": "already exists"})

    # Step 2: Transcribe
    if not video.transcript_s3_key:
        try:
            transcribe_task = transcribe_audio.delay(video.audio_s3_key, video.youtube_video_id)
            transcribe_result = transcribe_task.get(timeout=600)

            if transcribe_result["status"] == "success":
                video.transcript_s3_key = transcribe_result["transcript_s3_key"]
                db.add(video)
                db.commit()
                pipeline_status["steps"].append({"step": "transcribe", "status": "success"})
            else:
                pipeline_status["steps"].append({"step": "transcribe", "status": "failed", "error": transcribe_result.get("error")})
                return pipeline_status
        except Exception as e:
            pipeline_status["steps"].append({"step": "transcribe", "status": "failed", "error": str(e)})
            return pipeline_status
    else:
        pipeline_status["steps"].append({"step": "transcribe", "status": "skipped", "reason": "already exists"})

    # Step 3: Index in vector store
    try:
        storage_client = get_storage_client()
        transcript_data_raw = storage_client.get_object(video.transcript_s3_key)
        transcript_data = json.loads(transcript_data_raw.decode('utf-8'))

        vector_store = get_vector_store()
        chunks_count = vector_store.index_transcript(
            video_id=str(video.id),
            youtube_video_id=video.youtube_video_id,
            transcript_data=transcript_data,
            metadata={
                "views": video.views,
                "likes": video.likes,
                "title": video.title,
                "duration": video.duration_seconds
            }
        )

        pipeline_status["steps"].append({
            "step": "vector_index",
            "status": "success",
            "chunks_indexed": chunks_count
        })

    except Exception as e:
        pipeline_status["steps"].append({"step": "vector_index", "status": "failed", "error": str(e)})

    pipeline_status["complete"] = all(step["status"] in ["success", "skipped"] for step in pipeline_status["steps"])

    return pipeline_status
