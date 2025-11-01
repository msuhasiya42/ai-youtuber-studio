import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Channel, User
from typing import List, Optional
from pydantic import BaseModel
import jwt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleAuthRequest
from datetime import date, timedelta # New import for date calculations
from app.core.logging_config import get_logger, LogExecutionTime

logger = get_logger(__name__)
router = APIRouter()

# --- New Dependency to get current user ---
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
# --- End New Dependency ---

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")


class ChannelBase(BaseModel):
    id: int
    youtube_channel_id: str
    name: str
    avatar_url: Optional[str]
    subscribers: int
    verified: bool
    total_views: int
    total_watch_hours: float

    class Config:
        from_attributes = True


@router.post("/connect")
async def connect_channel(response: Response):
    """
    Initiates the YouTube channel connection process.
    """
    return {"message": "Channel connection process initiated via Google OAuth."}


@router.get("/me", response_model=ChannelBase)
async def get_my_channel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get information about the authenticated user's YouTube channel.
    """
    ch = db.query(Channel).filter(Channel.owner_id == current_user.id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="No channel found for this user.")
    return ch

# --- UPDATED ENDPOINT TO REFRESH CHANNEL DATA ---
@router.post("/{channel_id}/refresh", response_model=ChannelBase)
async def refresh_channel_data(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Refreshes the data for a specific channel from the YouTube Data API and Analytics API.
    """
    # 1. Verify channel belongs to current user
    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found or does not belong to user.")
    
    # 2. Get user's refresh token
    if not current_user.google_refresh_token:
        raise HTTPException(status_code=400, detail="User has no Google refresh token. Reconnect YouTube.")

    # 3. Use refresh token to get new access token
    creds = Credentials(
        token=None,
        refresh_token=current_user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/userinfo.email", "openid", "https://www.googleapis.com/auth/yt-analytics.readonly"],
    )
    
    try:
        creds.refresh(GoogleAuthRequest())
    except Exception as e:
        current_user.google_refresh_token = None
        db.add(current_user)
        db.commit()
        raise HTTPException(status_code=401, detail=f"Failed to refresh Google credentials: {e}. Please reconnect YouTube.")

    if creds.refresh_token and creds.refresh_token != current_user.google_refresh_token:
        current_user.google_refresh_token = creds.refresh_token
        db.add(current_user)
        db.commit()

    # 4. Fetch latest data from YouTube Data API
    total_views = 0
    subscribers = 0
    channel_name = channel.name
    avatar_url = channel.avatar_url
    is_verified = channel.verified

    try:
        youtube = build("youtube", "v3", credentials=creds)
        response_yt = youtube.channels().list(
            id=channel.youtube_channel_id,
            part="snippet,statistics"
        ).execute()

        if response_yt and response_yt.get("items"):
            channel_data_yt = response_yt["items"][0]
            channel_name = channel_data_yt["snippet"]["title"]
            avatar_url = channel_data_yt["snippet"]["thumbnails"]["default"]["url"]
            subscribers = int(channel_data_yt["statistics"].get("subscriberCount", 0))
            # Note: YouTube API doesn't provide a direct verification status field
            # Keep existing verification status or default to False
            is_verified = channel.verified  # Maintain existing verification status
            total_views = int(channel_data_yt["statistics"].get("viewCount", 0))
        else:
            print(f"No Data API channel info found for {channel.youtube_channel_id}.")

    except Exception as e:
        print(f"Error fetching YouTube Data API channel info for {channel.name}: {e}")
        # Proceed with existing data or defaults if Data API fails


    # --- NEW: Fetch total watch hours using YouTube Analytics API ---
    total_watch_hours = channel.total_watch_hours  # Default to existing value
    analytics_error = None
    try:
        youtube_analytics = build("youtubeAnalytics", "v2", credentials=creds)
        today = date.today().isoformat()
        start_date = "2000-01-01" # Arbitrary early date for all time

        analytics_response = youtube_analytics.reports().query(
            ids=f"channel=={channel.youtube_channel_id}",
            startDate=start_date,
            endDate=today,
            metrics="estimatedMinutesWatched"
        ).execute()

        if analytics_response and analytics_response.get("rows"):
            estimated_minutes_watched = analytics_response["rows"][0][0]
            total_watch_hours = float(estimated_minutes_watched) / 60.0
        else:
            analytics_error = "No watch hours data returned from Analytics API. Data may be delayed by 24-48 hours."
            print(f"Warning: {analytics_error} Channel: {channel.youtube_channel_id}")

    except Exception as e:
        analytics_error = str(e)
        print(f"Error fetching YouTube Analytics API watch hours for channel {channel.name}: {e}")
        print(f"Note: Analytics data may be unavailable or delayed. Using existing value: {total_watch_hours}")
        # Do not raise, keep existing value if analytics fails

    # Update existing channel object with all fetched data
    channel.name = channel_name
    channel.avatar_url = avatar_url
    channel.subscribers = subscribers
    channel.verified = is_verified
    channel.total_views = total_views
    channel.total_watch_hours = total_watch_hours

    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


# --- SYNC VIDEOS ENDPOINT ---
@router.post("/{channel_id}/sync-videos")
async def sync_channel_videos(
    channel_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sync videos from YouTube for the specified channel.
    Fetches latest videos and stores them in the database.
    """
    from app.services.youtube_client import YouTubeClient
    from app.models.models import Video

    logger.info(
        f"Sync videos request - channel_id={channel_id}, user_id={current_user.id}, limit={limit}"
    )

    # Verify channel belongs to current user
    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.owner_id == current_user.id
    ).first()

    if not channel:
        logger.warning(
            f"Sync failed: Channel {channel_id} not found or doesn't belong to user {current_user.id}"
        )
        raise HTTPException(status_code=404, detail="Channel not found or does not belong to user.")

    logger.info(f"Syncing channel: {channel.name} (youtube_id={channel.youtube_channel_id})")

    # Get user's refresh token
    if not current_user.google_refresh_token:
        logger.error(f"User {current_user.id} has no Google refresh token")
        raise HTTPException(status_code=400, detail="User has no Google refresh token. Reconnect YouTube.")

    # Refresh credentials
    logger.debug("Refreshing Google OAuth credentials")
    creds = Credentials(
        token=None,
        refresh_token=current_user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.readonly"],
    )

    try:
        creds.refresh(GoogleAuthRequest())
        logger.debug("Google OAuth credentials refreshed successfully")
    except Exception as e:
        logger.error(f"Failed to refresh credentials for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Failed to refresh credentials: {e}")

    # Fetch videos from YouTube
    youtube_client = YouTubeClient(credentials=creds)

    try:
        logger.info(f"Fetching {limit} videos from YouTube for channel {channel.youtube_channel_id}")
        with LogExecutionTime(logger, f"Fetch videos from YouTube", logging.INFO):
            videos_data = youtube_client.fetch_last_videos(
                channel_id=channel.youtube_channel_id,
                limit=limit,
                order="date"
            )
        logger.info(f"Successfully fetched {len(videos_data)} videos from YouTube")
    except Exception as e:
        logger.error(
            f"Failed to fetch videos from YouTube for channel {channel_id}: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch videos from YouTube: {e}")

    # Store videos in database and queue processing
    from app.services.pipeline_worker import queue_video_processing

    logger.info(f"Processing {len(videos_data)} videos for database storage")

    new_videos_count = 0
    updated_videos_count = 0
    queued_for_processing = 0

    for idx, video_data in enumerate(videos_data, 1):
        video_id = video_data["video_id"]
        video_title = video_data["title"]

        # Check if video already exists
        existing_video = db.query(Video).filter(
            Video.youtube_video_id == video_id
        ).first()

        if existing_video:
            # Update existing video
            logger.debug(f"[{idx}/{len(videos_data)}] Updating existing video: {video_id} - {video_title[:50]}")
            existing_video.title = video_data["title"]
            existing_video.thumbnail_url = video_data["thumbnail_url"]
            existing_video.duration_seconds = video_data["duration_seconds"]
            existing_video.published_at = video_data["published_at"]
            existing_video.views = video_data["views"]
            existing_video.likes = video_data["likes"]
            updated_videos_count += 1

            # Queue for processing if not yet processed or failed
            from app.models.models import VideoProcessingStatus
            if existing_video.processing_status in [VideoProcessingStatus.SYNCED, VideoProcessingStatus.ERROR]:
                try:
                    logger.debug(f"Queueing existing video {existing_video.id} for processing (status: {existing_video.processing_status})")
                    queue_video_processing.delay(existing_video.id, existing_video.youtube_video_id)
                    queued_for_processing += 1
                    logger.info(f"Successfully queued existing video {existing_video.id} ({video_id}) for processing")
                except Exception as e:
                    logger.warning(
                        f"Failed to queue existing video {existing_video.id} ({video_id}) for processing: {e}",
                        exc_info=True
                    )
        else:
            # Create new video
            logger.info(f"[{idx}/{len(videos_data)}] Creating new video: {video_id} - {video_title[:50]}")
            new_video = Video(
                channel_id=channel.id,
                youtube_video_id=video_id,
                title=video_data["title"],
                thumbnail_url=video_data["thumbnail_url"],
                duration_seconds=video_data["duration_seconds"],
                published_at=video_data["published_at"],
                views=video_data["views"],
                likes=video_data["likes"],
            )
            db.add(new_video)
            db.flush()  # Get the video ID without committing

            # Queue for processing
            try:
                logger.debug(f"Queueing video {new_video.id} for processing")
                queue_video_processing.delay(new_video.id, new_video.youtube_video_id)
                queued_for_processing += 1
                logger.info(f"Successfully queued video {new_video.id} ({video_id}) for processing")
            except Exception as e:
                logger.warning(
                    f"Failed to queue video {new_video.id} ({video_id}) for processing: {e}",
                    exc_info=True
                )

            new_videos_count += 1

    try:
        logger.debug("Committing database transaction")
        db.commit()
        logger.info(
            f"Sync complete - new: {new_videos_count}, updated: {updated_videos_count}, "
            f"queued: {queued_for_processing} (user_id={current_user.id}, channel_id={channel_id})"
        )
    except Exception as e:
        logger.error(f"Database commit failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save videos: {e}")

    return {
        "success": True,
        "new_videos": new_videos_count,
        "updated_videos": updated_videos_count,
        "total_fetched": len(videos_data),
        "queued_for_processing": queued_for_processing
    }