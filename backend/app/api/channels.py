import os
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
            is_verified = channel_data_yt["snippet"].get("liveStreamingDetails", {}).get("isVerified", False)
            total_views = int(channel_data_yt["statistics"].get("viewCount", 0))
        else:
            print(f"No Data API channel info found for {channel.youtube_channel_id}.")

    except Exception as e:
        print(f"Error fetching YouTube Data API channel info for {channel.name}: {e}")
        # Proceed with existing data or defaults if Data API fails


    # --- NEW: Fetch total watch hours using YouTube Analytics API ---
    total_watch_hours = 0.0
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
            print(f"No watch hours data found for channel {channel.youtube_channel_id} from Analytics API.")

    except Exception as e:
        print(f"Error fetching YouTube Analytics API watch hours for channel {channel.name}: {e}")
        # Do not raise, just use default 0.0 if analytics fails

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