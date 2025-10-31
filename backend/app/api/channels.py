import os
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Channel, User
from typing import List, Optional
from pydantic import BaseModel
import jwt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build # New import
from app.db.session import engine # New import
import os # New import

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

# New: Get Google Client ID and Secret for credential refresh
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

# --- NEW ENDPOINT TO REFRESH CHANNEL DATA ---
@router.post("/{channel_id}/refresh", response_model=ChannelBase)
async def refresh_channel_data(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Refreshes the data for a specific channel from the YouTube Data API.
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
        token=None,  # No initial access token
        refresh_token=current_user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    )
    # Refresh the credentials
    try:
        creds.refresh(engine=engine) # Use a dummy HTTP engine for refresh
    except Exception as e:
        # If refresh fails, the refresh token might be revoked or expired
        current_user.google_refresh_token = None # Clear invalid token
        db.add(current_user)
        db.commit()
        raise HTTPException(status_code=401, detail=f"Failed to refresh Google credentials: {e}. Please reconnect YouTube.")

    # Update user's refresh token if it changed during refresh (rare but possible)
    if creds.refresh_token and creds.refresh_token != current_user.google_refresh_token:
        current_user.google_refresh_token = creds.refresh_token
        db.add(current_user)
        db.commit()

    # 4. Fetch latest data from YouTube API
    try:
        youtube = build("youtube", "v3", credentials=creds)
        response_yt = youtube.channels().list(
            id=channel.youtube_channel_id, # Use specific channel ID
            part="snippet,contentDetails,statistics"
        ).execute()

        if response_yt and response_yt.get("items"):
            channel_data_yt = response_yt["items"][0]
            # Update existing channel object
            channel.name = channel_data_yt["snippet"]["title"]
            channel.avatar_url = channel_data_yt["snippet"]["thumbnails"]["default"]["url"]
            channel.subscribers = channel_data_yt["statistics"].get("subscriberCount", 0)
            channel.verified = channel_data_yt["snippet"].get("liveStreamingDetails", {}).get("isVerified", False)
            channel.total_views = channel_data_yt["statistics"].get("viewCount", 0)
            channel.total_watch_hours = 0.0 # Placeholder, as before

            db.add(channel)
            db.commit()
            db.refresh(channel)
            return channel
        else:
            raise HTTPException(status_code=404, detail="Could not retrieve updated channel data from YouTube.")

    except Exception as e:
        print(f"Error refreshing YouTube channel info for {channel.name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing YouTube channel info: {e}")
# --- END NEW ENDPOINT ---