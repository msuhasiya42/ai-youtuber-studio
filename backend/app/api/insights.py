from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Video, Channel, VideoRetentionCurve, VideoTrafficSource, AIInsight
from app.services.advanced_pattern_analyzer import AdvancedPatternAnalyzer
from app.services.insights_generation_prompts import InsightsPromptTemplates
from app.services.llm_provider import get_llm_provider
from app.core.logging_config import get_logger
from datetime import datetime, timedelta
from typing import Optional
import json

router = APIRouter()
logger = get_logger(__name__)


@router.get("")
def top_performers(db: Session = Depends(get_db)):
    """Legacy endpoint - get top performing videos with basic insights."""
    vids = db.query(Video).order_by(Video.views.desc()).limit(5).all()
    # Placeholder insights
    insights = {
        "drivers": ["Engaging hooks", "Clear thumbnails"],
        "patterns": ["8-10 minute length", "Actionable titles"],
        "suggestions": ["Try A/B testing titles", "Experiment with first 15s hook"],
    }
    return {
        "videos": [
            {"id": v.id, "title": v.title, "views": v.views, "likes": v.likes, "ctr": v.ctr}
            for v in vids
        ],
        "insights": insights,
    }


@router.get("/comprehensive/{channel_id}")
async def get_comprehensive_insights(
    channel_id: int,
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive AI-powered insights for a channel.
    Results are cached for 24 hours unless force_refresh=True.
    """
    logger.info(f"Fetching comprehensive insights for channel {channel_id} (force_refresh={force_refresh})")

    # Check for cached insights
    if not force_refresh:
        cached_insight = db.query(AIInsight).filter(
            AIInsight.channel_id == channel_id,
            AIInsight.insight_type == 'comprehensive',
            AIInsight.expires_at > datetime.now()
        ).first()

        if cached_insight:
            logger.info(f"Returning cached insights for channel {channel_id}")
            return {
                'channel_id': channel_id,
                'cached': True,
                'generated_at': cached_insight.generated_at.isoformat(),
                'expires_at': cached_insight.expires_at.isoformat(),
                **cached_insight.insight_data
            }

    # Generate fresh insights
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    analyzer = AdvancedPatternAnalyzer(db, channel_id)
    comprehensive_data = analyzer.get_comprehensive_insights()

    # Cache the results
    expires_at = datetime.now() + timedelta(hours=24)

    # Upsert AI insight
    existing_insight = db.query(AIInsight).filter(
        AIInsight.channel_id == channel_id,
        AIInsight.insight_type == 'comprehensive'
    ).first()

    if existing_insight:
        existing_insight.insight_data = comprehensive_data
        existing_insight.generated_at = datetime.now()
        existing_insight.expires_at = expires_at
        existing_insight.videos_analyzed = len(db.query(Video).filter(
            Video.channel_id == channel_id,
            Video.analytics_available == True
        ).all())
    else:
        new_insight = AIInsight(
            channel_id=channel_id,
            insight_type='comprehensive',
            insight_data=comprehensive_data,
            generated_at=datetime.now(),
            expires_at=expires_at,
            videos_analyzed=len(db.query(Video).filter(
                Video.channel_id == channel_id,
                Video.analytics_available == True
            ).all())
        )
        db.add(new_insight)

    db.commit()

    logger.info(f"Generated and cached comprehensive insights for channel {channel_id}")

    return {
        'channel_id': channel_id,
        'cached': False,
        'generated_at': datetime.now().isoformat(),
        'expires_at': expires_at.isoformat(),
        **comprehensive_data
    }


@router.get("/performance-drivers/{channel_id}")
async def get_performance_drivers(
    channel_id: int,
    use_llm: bool = True,
    db: Session = Depends(get_db)
):
    """
    Identify what makes top videos successful.
    Uses LLM for narrative insights if use_llm=True.
    """
    logger.info(f"Analyzing performance drivers for channel {channel_id} (use_llm={use_llm})")

    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Get top 10 videos
    top_videos = db.query(Video).filter(
        Video.channel_id == channel_id,
        Video.analytics_available == True
    ).order_by(Video.views.desc()).limit(10).all()

    if not top_videos:
        raise HTTPException(
            status_code=404,
            detail="No analytics data available. Sync analytics first."
        )

    # Prepare video data
    video_data = []
    for video in top_videos:
        # Get traffic sources
        top_traffic = db.query(VideoTrafficSource).filter(
            VideoTrafficSource.video_id == video.id
        ).order_by(VideoTrafficSource.views.desc()).first()

        video_data.append({
            'title': video.title,
            'views': video.views,
            'retention': video.average_view_percentage or 0,
            'hook_strength': video.hook_strength or 0,
            'engagement_rate': video.engagement_rate,
            'duration_minutes': round(video.duration_seconds / 60, 1),
            'subscribers_gained': video.subscribers_gained,
            'first_24h_views': video.first_24h_views or 0,
            'top_traffic_source': top_traffic.source_type if top_traffic else 'N/A',
            'traffic_percentage': top_traffic.percentage_of_views if top_traffic else 0
        })

    if not use_llm:
        return {
            'channel_id': channel_id,
            'top_videos': video_data,
            'use_llm': False
        }

    # Generate LLM insights
    try:
        prompt = InsightsPromptTemplates.performance_drivers_prompt(video_data, top_n=10)
        llm_provider = get_llm_provider()
        response = llm_provider.generate(prompt)

        # Parse JSON response
        insights_json = json.loads(response)

        logger.info(f"Generated LLM performance driver insights for channel {channel_id}")

        return {
            'channel_id': channel_id,
            'channel_name': channel.name,
            'videos_analyzed': len(video_data),
            'use_llm': True,
            **insights_json,
            'raw_video_data': video_data
        }

    except Exception as e:
        logger.error(f"Error generating LLM insights: {e}", exc_info=True)
        return {
            'channel_id': channel_id,
            'error': 'Failed to generate LLM insights',
            'raw_video_data': video_data
        }


@router.get("/retention-analysis/{video_id}")
async def get_retention_analysis(
    video_id: int,
    use_llm: bool = True,
    db: Session = Depends(get_db)
):
    """
    Deep dive into retention patterns for a specific video.
    Uses LLM to correlate retention drops with content moments.
    """
    logger.info(f"Analyzing retention for video {video_id} (use_llm={use_llm})")

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

    # Prepare retention data
    retention_milestones = {
        '10s': retention_curve.retention_at_10s or 0,
        '30s': retention_curve.retention_at_30s or 0,
        '60s': retention_curve.retention_at_60s or 0,
        'halfway': retention_curve.retention_at_halfway or 0,
        'end': retention_curve.retention_at_end or 0
    }

    # Find significant drops
    retention_points = retention_curve.retention_points
    significant_drops = []

    if isinstance(retention_points, list) and len(retention_points) > 1:
        for i in range(1, len(retention_points)):
            drop = retention_points[i - 1].get('retention_percentage', 0) - retention_points[i].get('retention_percentage', 0)
            if drop > 5:  # >5% drop is significant
                significant_drops.append({
                    'timestamp': retention_points[i].get('elapsed_seconds', 0),
                    'drop_percentage': drop
                })

    video_stats = {
        'views': video.views,
        'average_retention': video.average_view_percentage or 0,
        'duration_minutes': round(video.duration_seconds / 60, 1),
        'engagement_rate': video.engagement_rate
    }

    if not use_llm:
        return {
            'video_id': video_id,
            'youtube_video_id': video.youtube_video_id,
            'title': video.title,
            'retention_milestones': retention_milestones,
            'significant_drops': significant_drops,
            'video_stats': video_stats,
            'use_llm': False
        }

    # Generate LLM insights
    try:
        prompt = InsightsPromptTemplates.retention_analysis_prompt(
            video.title,
            video_stats,
            retention_milestones,
            significant_drops
        )
        llm_provider = get_llm_provider()
        response = llm_provider.generate(prompt)

        # Parse JSON response
        insights_json = json.loads(response)

        logger.info(f"Generated LLM retention insights for video {video_id}")

        return {
            'video_id': video_id,
            'youtube_video_id': video.youtube_video_id,
            'title': video.title,
            'use_llm': True,
            **insights_json,
            'raw_data': {
                'retention_milestones': retention_milestones,
                'significant_drops': significant_drops,
                'video_stats': video_stats
            }
        }

    except Exception as e:
        logger.error(f"Error generating LLM retention insights: {e}", exc_info=True)
        return {
            'video_id': video_id,
            'error': 'Failed to generate LLM insights',
            'retention_milestones': retention_milestones,
            'significant_drops': significant_drops,
            'video_stats': video_stats
        }
