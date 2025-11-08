from celery import group
from celery_worker import app as celery_app
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import (
    Video, VideoAnalyticsDaily, VideoRetentionCurve,
    VideoTrafficSource, ChannelDemographics, User, Channel
)
from app.services.youtube_analytics_client import YouTubeAnalyticsClient
from app.db.session import SessionLocal
from google.oauth2.credentials import Credentials
from app.core.logging_config import get_logger
from typing import List, Dict, Optional
import statistics

logger = get_logger(__name__)


def get_youtube_analytics_client(user: User) -> Optional[YouTubeAnalyticsClient]:
    """
    Build YouTube Analytics client from user's refresh token.

    Args:
        user: User model with google_refresh_token

    Returns:
        YouTubeAnalyticsClient or None if credentials unavailable
    """
    if not user.google_refresh_token:
        logger.error(f"No OAuth token for user {user.id}")
        return None

    try:
        # Refresh credentials from stored token
        credentials = Credentials(
            token=None,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=None,  # Will be loaded from environment
            client_secret=None  # Will be loaded from environment
        )

        return YouTubeAnalyticsClient(credentials)
    except Exception as e:
        logger.error(f"Failed to create analytics client for user {user.id}: {e}", exc_info=True)
        return None


@celery_app.task(bind=True, max_retries=3)
def sync_video_analytics(self, video_id: int, days_back: int = 30):
    """
    Sync analytics for a single video from YouTube Analytics API.

    Args:
        video_id: Database video ID
        days_back: How many days of historical data to fetch
    """
    db: Session = SessionLocal()

    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found")
            return

        # Get user's YouTube credentials
        user = video.channel.owner
        analytics_client = get_youtube_analytics_client(user)
        if not analytics_client:
            return

        # Calculate date range
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # Fetch comprehensive analytics
        metrics = analytics_client.fetch_video_analytics(
            video.youtube_video_id,
            start_date,
            end_date
        )

        if not metrics:
            logger.warning(f"No analytics data for video {video.youtube_video_id}")
            video.analytics_available = False
            db.commit()
            return

        # Update video model with latest metrics
        video.average_view_duration_seconds = metrics.get('averageViewDuration')
        video.average_view_percentage = metrics.get('averageViewPercentage')
        video.estimated_minutes_watched = metrics.get('estimatedMinutesWatched')
        video.subscribers_gained = metrics.get('subscribersGained', 0)
        video.subscribers_lost = metrics.get('subscribersLost', 0)
        video.shares = metrics.get('shares', 0)
        video.videos_added_to_playlists = metrics.get('videosAddedToPlaylists', 0)
        video.last_analytics_sync_at = datetime.now()
        video.analytics_available = True

        # Fetch retention curve
        retention_data = analytics_client.fetch_retention_curve(video.youtube_video_id)
        if retention_data:
            store_retention_curve(db, video, retention_data)

        # Fetch traffic sources
        traffic_sources = analytics_client.fetch_traffic_sources(
            video.youtube_video_id,
            start_date,
            end_date
        )
        if traffic_sources:
            store_traffic_sources(db, video, traffic_sources)

        # Fetch first 24h performance if available
        if video.published_at and not video.first_24h_views:
            first_24h_views = analytics_client.fetch_first_24h_performance(
                video.youtube_video_id,
                video.published_at
            )
            if first_24h_views is not None:
                video.first_24h_views = first_24h_views

        db.commit()
        logger.info(f"Successfully synced analytics for video {video.youtube_video_id}")

        return {
            'video_id': video_id,
            'youtube_video_id': video.youtube_video_id,
            'metrics_updated': len(metrics),
            'retention_curve_available': retention_data is not None,
            'traffic_sources_count': len(traffic_sources)
        }

    except Exception as e:
        logger.error(f"Error syncing analytics for video {video_id}: {e}", exc_info=True)
        db.rollback()
        raise self.retry(exc=e, countdown=60)  # Retry after 1 minute

    finally:
        db.close()


@celery_app.task
def sync_channel_analytics_batch(channel_id: int, limit: int = 50):
    """
    Sync analytics for all videos in a channel (batched for efficiency).

    Args:
        channel_id: Database channel ID
        limit: Max number of videos to sync
    """
    db: Session = SessionLocal()

    try:
        # Get videos that need analytics sync
        videos = db.query(Video).filter(
            Video.channel_id == channel_id,
        ).order_by(
            Video.published_at.desc()
        ).limit(limit).all()

        if not videos:
            logger.info(f"No videos to sync for channel {channel_id}")
            return

        # Create parallel tasks for each video
        job = group(
            sync_video_analytics.s(video.id, days_back=90)
            for video in videos
        )

        result = job.apply_async()

        logger.info(f"Queued {len(videos)} videos for analytics sync")

        return {
            'channel_id': channel_id,
            'videos_queued': len(videos),
            'task_group_id': result.id
        }

    finally:
        db.close()


@celery_app.task
def sync_channel_demographics(channel_id: int, days_back: int = 30):
    """
    Sync audience demographics for a channel.

    Args:
        channel_id: Database channel ID
        days_back: Days of data to analyze
    """
    db: Session = SessionLocal()

    try:
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            logger.error(f"Channel {channel_id} not found")
            return

        # Get analytics client
        analytics_client = get_youtube_analytics_client(channel.owner)
        if not analytics_client:
            return

        # Calculate date range
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # Fetch demographics
        demographics = analytics_client.fetch_channel_demographics(start_date, end_date)

        snapshot_date = datetime.now()

        # Clear old demographics data
        db.query(ChannelDemographics).filter(
            ChannelDemographics.channel_id == channel_id
        ).delete()

        # Store age groups
        for age_data in demographics.get('age_groups', []):
            demo = ChannelDemographics(
                channel_id=channel_id,
                dimension_type='age_group',
                dimension_value=age_data['group'],
                views_percentage=age_data['percentage'],
                snapshot_date=snapshot_date
            )
            db.add(demo)

        # Store genders
        for gender_data in demographics.get('genders', []):
            demo = ChannelDemographics(
                channel_id=channel_id,
                dimension_type='gender',
                dimension_value=gender_data['gender'],
                views_percentage=gender_data['percentage'],
                snapshot_date=snapshot_date
            )
            db.add(demo)

        # Store countries
        for country_data in demographics.get('countries', []):
            demo = ChannelDemographics(
                channel_id=channel_id,
                dimension_type='geography',
                dimension_value=country_data['country'],
                views_percentage=country_data['percentage'],
                snapshot_date=snapshot_date
            )
            db.add(demo)

        db.commit()
        logger.info(f"Successfully synced demographics for channel {channel_id}")

        return {
            'channel_id': channel_id,
            'age_groups_count': len(demographics.get('age_groups', [])),
            'genders_count': len(demographics.get('genders', [])),
            'countries_count': len(demographics.get('countries', []))
        }

    except Exception as e:
        logger.error(f"Error syncing demographics for channel {channel_id}: {e}", exc_info=True)
        db.rollback()
        return None

    finally:
        db.close()


@celery_app.task
def daily_analytics_refresh():
    """
    Scheduled task: Refresh analytics for all active channels daily.

    Should be run via Celery Beat at 3 AM UTC.
    """
    db: Session = SessionLocal()

    try:
        # Get all channels with OAuth tokens
        channels = db.query(Channel).join(User).filter(
            User.google_refresh_token.isnot(None)
        ).all()

        logger.info(f"Starting daily refresh for {len(channels)} channels")

        # Queue batch sync for each channel
        for channel in channels:
            sync_channel_analytics_batch.delay(channel.id, limit=100)

        return {
            'channels_refreshed': len(channels),
            'timestamp': datetime.now().isoformat()
        }

    finally:
        db.close()


def store_retention_curve(db: Session, video: Video, retention_data: List[Dict]):
    """
    Store retention curve data with key milestones.

    Args:
        db: Database session
        video: Video model
        retention_data: List of {elapsed_ratio, retention_ratio}
    """
    # Calculate duration in seconds
    duration = video.duration_seconds

    # Extract key milestones
    retention_at_10s = get_retention_at_time(retention_data, 10, duration)
    retention_at_30s = get_retention_at_time(retention_data, 30, duration)
    retention_at_60s = get_retention_at_time(retention_data, 60, duration)
    retention_at_halfway = get_retention_at_time(retention_data, duration / 2, duration)
    retention_at_end = retention_data[-1]['retention_ratio'] * 100 if retention_data else 0

    # Calculate median retention
    median_retention = sum(point['retention_ratio'] for point in retention_data) / len(retention_data) * 100 if retention_data else 0

    # Find critical drop point
    critical_drop_point = find_critical_drop_point(retention_data, duration)

    # Convert retention data to storable format
    retention_points_json = [
        {
            'elapsed_seconds': int(point['elapsed_ratio'] * duration),
            'retention_percentage': point['retention_ratio'] * 100
        }
        for point in retention_data
    ]

    # Upsert retention curve
    retention_curve = db.query(VideoRetentionCurve).filter(
        VideoRetentionCurve.video_id == video.id
    ).first()

    if not retention_curve:
        retention_curve = VideoRetentionCurve(video_id=video.id)
        db.add(retention_curve)

    retention_curve.retention_points = retention_points_json
    retention_curve.retention_at_10s = retention_at_10s
    retention_curve.retention_at_30s = retention_at_30s
    retention_curve.retention_at_60s = retention_at_60s
    retention_curve.retention_at_halfway = retention_at_halfway
    retention_curve.retention_at_end = retention_at_end
    retention_curve.median_retention_percentage = median_retention
    retention_curve.critical_drop_point_seconds = critical_drop_point
    retention_curve.synced_at = datetime.now()

    db.commit()
    logger.info(f"Stored retention curve for video {video.youtube_video_id}")


def store_traffic_sources(db: Session, video: Video, traffic_sources: List[Dict]):
    """
    Store traffic source breakdown.

    Args:
        db: Database session
        video: Video model
        traffic_sources: List of {source_type, views, watch_time_minutes, percentage}
    """
    # Clear existing traffic sources
    db.query(VideoTrafficSource).filter(
        VideoTrafficSource.video_id == video.id
    ).delete()

    # Insert new traffic sources
    for source in traffic_sources:
        traffic_source = VideoTrafficSource(
            video_id=video.id,
            source_type=source['source_type'],
            views=source['views'],
            watch_time_minutes=source['watch_time_minutes'],
            percentage_of_views=source['percentage']
        )
        db.add(traffic_source)

    db.commit()
    logger.info(f"Stored {len(traffic_sources)} traffic sources for video {video.youtube_video_id}")


def get_retention_at_time(retention_data: List[Dict], target_seconds: float, duration: int) -> float:
    """
    Get retention percentage at specific timestamp.

    Args:
        retention_data: List of retention points
        target_seconds: Target timestamp in seconds
        duration: Video duration in seconds

    Returns:
        Retention percentage at target time
    """
    target_ratio = target_seconds / duration if duration > 0 else 0

    # Find closest data point
    for point in retention_data:
        if point['elapsed_ratio'] >= target_ratio:
            return point['retention_ratio'] * 100

    return 0.0


def find_critical_drop_point(retention_data: List[Dict], duration: int) -> int:
    """
    Find the point where retention drops most significantly.

    Args:
        retention_data: List of retention points
        duration: Video duration in seconds

    Returns:
        Timestamp in seconds where biggest drop occurs
    """
    if not retention_data or len(retention_data) < 2:
        return 0

    max_drop = 0
    critical_point = 0

    for i in range(1, len(retention_data)):
        drop = retention_data[i - 1]['retention_ratio'] - retention_data[i]['retention_ratio']
        if drop > max_drop:
            max_drop = drop
            critical_point = retention_data[i]['elapsed_ratio'] * duration

    return int(critical_point)
