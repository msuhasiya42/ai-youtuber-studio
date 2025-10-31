import os
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from urllib.parse import urlencode
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import jwt
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, Channel
from datetime import datetime, date, timedelta # New import for date calculations

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Change this to your deployed frontend URL in production
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
# This must also be whitelisted in your Google Cloud OAuth "Authorized redirect URIs"
REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI") or "http://localhost:8000/api/auth/oauth/google/callback"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/yt-analytics.readonly", # NEW SCOPE
]

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for dev!

@router.get("/oauth/google/url")
async def get_google_oauth_url(request: Request):

    print(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
    flow = Flow.from_client_config(
        {"web": {"client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # Save state in cookie/session if needed
    return {"url": authorization_url}


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    request: Request, response: Response, code: str, db: Session = Depends(get_db)
):
    """
    Handles Google OAuth redirect, exchanges code for token, fetches user/channel info, persists user/session.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth credentials not configured.")

    flow = Flow.from_client_config(
        {"web": {"client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Error fetching token: {e}"})

    creds = flow.credentials
    if not creds.id_token:
        raise HTTPException(status_code=400, detail="No ID token received.")

    # Decode ID token to get user's email
    id_info = jwt.decode(creds.id_token, options={"verify_signature": False})
    user_email = id_info.get("email")

    if not user_email:
        raise HTTPException(status_code=400, detail="Could not retrieve user email from ID token.")

    # Find or create user
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Store refresh token
    user.google_refresh_token = creds.refresh_token
    db.add(user)
    db.commit()
    db.refresh(user)

    # Use access token to get YouTube channel info (Data API)
    total_views = 0
    subscribers = 0
    youtube_channel_id = None
    channel_name = "Unknown Channel"
    avatar_url = None
    is_verified = False

    try:
        youtube = build("youtube", "v3", credentials=creds)
        response_yt = youtube.channels().list(
            mine=True,
            part="snippet,statistics"
        ).execute()

        if response_yt and response_yt.get("items"):
            channel_data = response_yt["items"][0]
            youtube_channel_id = channel_data["id"]
            channel_name = channel_data["snippet"]["title"]
            avatar_url = channel_data["snippet"]["thumbnails"]["default"]["url"]
            subscribers = int(channel_data["statistics"].get("subscriberCount", 0))
            is_verified = channel_data["snippet"].get("liveStreamingDetails", {}).get("isVerified", False)
            total_views = int(channel_data["statistics"].get("viewCount", 0))
        else:
            print(f"No YouTube channel found via Data API for the authenticated user.")

    except Exception as e:
        print(f"Error fetching YouTube Data API channel info: {e}")
        # Don't raise here, try to proceed to Analytics API if basic data fetched

    # --- NEW: Fetch total watch hours using YouTube Analytics API ---
    total_watch_hours = 0.0
    if youtube_channel_id: # Only proceed if we found a channel ID from Data API
        try:
            youtube_analytics = build("youtubeAnalytics", "v2", credentials=creds)
            # Fetch all-time data
            today = date.today().isoformat()
            # An arbitrary early date for 'all time' if channel creation date isn't easily available
            start_date = "2000-01-01" 

            analytics_response = youtube_analytics.reports().query(
                ids=f"channel=={youtube_channel_id}",
                startDate=start_date,
                endDate=today,
                metrics="estimatedMinutesWatched"
            ).execute()

            if analytics_response and analytics_response.get("rows"):
                estimated_minutes_watched = analytics_response["rows"][0][0]
                total_watch_hours = float(estimated_minutes_watched) / 60.0
            else:
                print(f"No watch hours data found for channel {youtube_channel_id} from Analytics API.")

        except Exception as e:
            print(f"Error fetching YouTube Analytics API watch hours for channel {youtube_channel_id}: {e}")
            # Do not raise, just use default 0.0 if analytics fails
    # --- END NEW: Fetch total watch hours ---


    # Find or create channel and update all fields
    channel = db.query(Channel).filter(Channel.youtube_channel_id == youtube_channel_id).first()
    if not channel:
        channel = Channel(
            owner_id=user.id,
            youtube_channel_id=youtube_channel_id,
            name=channel_name,
            avatar_url=avatar_url,
            subscribers=subscribers,
            verified=is_verified,
            total_views=total_views,
            total_watch_hours=total_watch_hours
        )
        db.add(channel)
    else:
        # Update existing channel info
        channel.name = channel_name
        channel.avatar_url = avatar_url
        channel.subscribers = subscribers
        channel.verified = is_verified
        channel.total_views = total_views
        channel.total_watch_hours = total_watch_hours
    db.commit()
    db.refresh(channel)

    # Create a RedirectResponse explicitly
    redirect_response = RedirectResponse(FRONTEND_URL)
    # Set the cookie directly on the redirect_response object
    redirect_response.set_cookie(key="user_id", value=str(user.id), httponly=True, secure=False, samesite="Lax", domain="localhost")

    return redirect_response