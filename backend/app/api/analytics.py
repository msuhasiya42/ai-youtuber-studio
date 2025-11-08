from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Video, Channel, VideoRetentionCurve, VideoTrafficSource, User
from app.services.analytics_sync_worker import sync_video_analytics, sync_channel_analytics_batch, sync_channel_demographics
from app.services.advanced_pattern_analyzer import AdvancedPatternAnalyzer
from app.core.logging_config import get_logger
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter()
logger = get_logger(__name__)


# Request/Response Models

class SyncAnalyticsRequest(BaseModel):
    days_back: Optional[int] = 30


class SyncAnalyticsResponse(BaseModel):
    message: str
    videos_queued: int
    channel_id: int


class VideoAnalyticsResponse(BaseModel):
    video_id: int
    youtube_video_id: str
    title: str
    views: int
    likes: int
    comments: int
    shares: int
    average_view_duration_seconds: Optional[int]
    average_view_percentage: Optional[float]
    estimated_minutes_watched: Optional[int]
    subscribers_gained: int
    subscribers_lost: int
    first_24h_views: Optional[int]
    engagement_rate: float
    subscriber_conversion_rate: float
    hook_strength: Optional[float]
    analytics_available: bool
    last_analytics_sync_at: Optional[str]


class RetentionCurveResponse(BaseModel):
    video_id: int
    youtube_video_id: str
    title: str
    retention_points: list
    retention_at_10s: Optional[float]
    retention_at_30s: Optional[float]
    retention_at_60s: Optional[float]
    retention_at_halfway: Optional[float]
    retention_at_end: Optional[float]
    median_retention_percentage: Optional[float]
    critical_drop_point_seconds: Optional[int]


class TrafficSourceResponse(BaseModel):
    video_id: int
    youtube_video_id: str
    title: str
    traffic_sources: List[dict]


# Endpoints

@router.post("/sync/{channel_id}", response_model=SyncAnalyticsResponse)
async def sync_channel_analytics(
    channel_id: int,
    request: SyncAnalyticsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger analytics sync for a channel.
    Runs asynchronously in the background.
    """
    logger.info(f"Analytics sync requested for channel {channel_id}")

    # Verify channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Verify user has OAuth token
    if not channel.owner or not channel.owner.google_refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Channel owner must connect YouTube account first"
        )

    # Count videos to sync
    videos_count = db.query(Video).filter(Video.channel_id == channel_id).count()

    # Queue sync task
    background_tasks.add_task(
        sync_channel_analytics_batch.delay,
        channel_id=channel_id,
        limit=100
    )

    logger.info(f"Queued analytics sync for {videos_count} videos")

    return SyncAnalyticsResponse(
        message="Analytics sync started",
        videos_queued=min(videos_count, 100),
        channel_id=channel_id
    )


@router.get("/video/{video_id}", response_model=VideoAnalyticsResponse)
async def get_video_analytics(video_id: int, db: Session = Depends(get_db)):
    """
    Get comprehensive analytics for a single video.
    """
    logger.info(f"Fetching analytics for video {video_id}")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return VideoAnalyticsResponse(
        video_id=video.id,
        youtube_video_id=video.youtube_video_id,
        title=video.title,
        views=video.views,
        likes=video.likes,
        comments=video.comments,
        shares=video.shares,
        average_view_duration_seconds=video.average_view_duration_seconds,
        average_view_percentage=video.average_view_percentage,
        estimated_minutes_watched=video.estimated_minutes_watched,
        subscribers_gained=video.subscribers_gained,
        subscribers_lost=video.subscribers_lost,
        first_24h_views=video.first_24h_views,
        engagement_rate=video.engagement_rate,
        subscriber_conversion_rate=video.subscriber_conversion_rate,
        hook_strength=video.hook_strength,
        analytics_available=video.analytics_available,
        last_analytics_sync_at=video.last_analytics_sync_at.isoformat() if video.last_analytics_sync_at else None
    )


@router.get("/retention/{video_id}", response_model=RetentionCurveResponse)
async def get_retention_curve(video_id: int, db: Session = Depends(get_db)):
    """
    Get retention curve data for a video.
    """
    logger.info(f"Fetching retention curve for video {video_id}")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    retention_curve = db.query(VideoRetentionCurve).filter(
        VideoRetentionCurve.video_id == video_id
    ).first()

    if not retention_curve:
        raise HTTPException(
            status_code=404,
            detail="Retention curve not available for this video"
        )

    return RetentionCurveResponse(
        video_id=video.id,
        youtube_video_id=video.youtube_video_id,
        title=video.title,
        retention_points=retention_curve.retention_points,
        retention_at_10s=retention_curve.retention_at_10s,
        retention_at_30s=retention_curve.retention_at_30s,
        retention_at_60s=retention_curve.retention_at_60s,
        retention_at_halfway=retention_curve.retention_at_halfway,
        retention_at_end=retention_curve.retention_at_end,
        median_retention_percentage=retention_curve.median_retention_percentage,
        critical_drop_point_seconds=retention_curve.critical_drop_point_seconds
    )


@router.get("/traffic-sources/{video_id}", response_model=TrafficSourceResponse)
async def get_traffic_sources(video_id: int, db: Session = Depends(get_db)):
    """
    Get traffic source breakdown for a video.
    """
    logger.info(f"Fetching traffic sources for video {video_id}")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    traffic_sources = db.query(VideoTrafficSource).filter(
        VideoTrafficSource.video_id == video_id
    ).all()

    traffic_data = [
        {
            'source_type': source.source_type,
            'source_detail': source.source_detail,
            'views': source.views,
            'watch_time_minutes': source.watch_time_minutes,
            'percentage_of_views': source.percentage_of_views
        }
        for source in traffic_sources
    ]

    return TrafficSourceResponse(
        video_id=video.id,
        youtube_video_id=video.youtube_video_id,
        title=video.title,
        traffic_sources=traffic_data
    )


@router.get("/channel/{channel_id}/summary")
async def get_channel_analytics_summary(channel_id: int, db: Session = Depends(get_db)):
    """
    Get analytics summary for entire channel.
    """
    logger.info(f"Fetching analytics summary for channel {channel_id}")

    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Get all videos with analytics
    videos = db.query(Video).filter(
        Video.channel_id == channel_id,
        Video.analytics_available == True
    ).all()

    if not videos:
        return {
            'channel_id': channel_id,
            'message': 'No analytics data available yet. Sync analytics first.',
            'total_videos': db.query(Video).filter(Video.channel_id == channel_id).count()
        }

    # Calculate aggregates
    import statistics

    total_views = sum(v.views for v in videos)
    total_watch_time = sum(v.estimated_minutes_watched or 0 for v in videos)
    avg_retention = statistics.mean([v.average_view_percentage for v in videos if v.average_view_percentage])
    avg_engagement = statistics.mean([v.engagement_rate for v in videos])
    total_subscribers_gained = sum(v.subscribers_gained for v in videos)

    # Get videos with retention curves
    videos_with_hooks = [v for v in videos if v.hook_strength is not None]
    avg_hook_strength = statistics.mean([v.hook_strength for v in videos_with_hooks]) if videos_with_hooks else None

    return {
        'channel_id': channel_id,
        'channel_name': channel.name,
        'total_videos_analyzed': len(videos),
        'total_videos': db.query(Video).filter(Video.channel_id == channel_id).count(),
        'summary': {
            'total_views': total_views,
            'total_watch_time_minutes': total_watch_time,
            'total_watch_time_hours': round(total_watch_time / 60, 2),
            'avg_views_per_video': round(total_views / len(videos), 0),
            'avg_retention_percentage': round(avg_retention, 2),
            'avg_engagement_rate': round(avg_engagement, 2),
            'avg_hook_strength': round(avg_hook_strength, 2) if avg_hook_strength else None,
            'total_subscribers_gained': total_subscribers_gained
        },
        'top_performers': [
            {
                'video_id': v.id,
                'youtube_video_id': v.youtube_video_id,
                'title': v.title,
                'views': v.views,
                'retention': v.average_view_percentage,
                'engagement_rate': v.engagement_rate,
                'hook_strength': v.hook_strength
            }
            for v in sorted(videos, key=lambda x: x.views, reverse=True)[:5]
        ]
    }


@router.get("/pattern-analysis/retention-by-duration/{channel_id}")
async def analyze_retention_by_duration(channel_id: int, db: Session = Depends(get_db)):
    """
    Analyze correlation between video duration and retention.
    """
    logger.info(f"Analyzing retention by duration for channel {channel_id}")

    analyzer = AdvancedPatternAnalyzer(db, channel_id)
    return analyzer.analyze_retention_by_duration()


@router.get("/pattern-analysis/hook-effectiveness/{channel_id}")
async def analyze_hook_effectiveness(channel_id: int, db: Session = Depends(get_db)):
    """
    Analyze hook effectiveness (first 30 seconds retention).
    """
    logger.info(f"Analyzing hook effectiveness for channel {channel_id}")

    analyzer = AdvancedPatternAnalyzer(db, channel_id)
    return analyzer.analyze_hook_effectiveness()


@router.get("/pattern-analysis/traffic-sources/{channel_id}")
async def analyze_traffic_sources(channel_id: int, db: Session = Depends(get_db)):
    """
    Analyze traffic source performance.
    """
    logger.info(f"Analyzing traffic sources for channel {channel_id}")

    analyzer = AdvancedPatternAnalyzer(db, channel_id)
    return analyzer.analyze_traffic_source_performance()


@router.get("/pattern-analysis/posting-time/{channel_id}")
async def analyze_posting_time(channel_id: int, db: Session = Depends(get_db)):
    """
    Analyze optimal posting time/day.
    """
    logger.info(f"Analyzing posting time for channel {channel_id}")

    analyzer = AdvancedPatternAnalyzer(db, channel_id)
    return analyzer.analyze_optimal_posting_time()


@router.get("/pattern-analysis/engagement/{channel_id}")
async def analyze_engagement_patterns(channel_id: int, db: Session = Depends(get_db)):
    """
    Analyze engagement patterns.
    """
    logger.info(f"Analyzing engagement patterns for channel {channel_id}")

    analyzer = AdvancedPatternAnalyzer(db, channel_id)
    return analyzer.analyze_engagement_patterns()


@router.get("/recommendations/{channel_id}")
async def get_content_recommendations(channel_id: int, db: Session = Depends(get_db)):
    """
    Get AI-powered content recommendations based on analytics.
    """
    logger.info(f"Generating content recommendations for channel {channel_id}")

    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    analyzer = AdvancedPatternAnalyzer(db, channel_id)
    return analyzer.generate_content_recommendations()
