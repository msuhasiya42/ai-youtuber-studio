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
    id_info = jwt.decode(creds.id_token, options={"verify_signature": False}) # For verification, you'd add Google's public keys
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

    # Use access token to get YouTube channel info
    try:
        youtube = build("youtube", "v3", credentials=creds)
        response_yt = youtube.channels().list(
            mine=True,
            part="snippet,contentDetails,statistics"
        ).execute()

        if response_yt and response_yt.get("items"):
            channel_data = response_yt["items"][0]
            youtube_channel_id = channel_data["id"]
            channel_name = channel_data["snippet"]["title"]
            avatar_url = channel_data["snippet"]["thumbnails"]["default"]["url"]
            subscribers = channel_data["statistics"].get("subscriberCount", 0)
            is_verified = channel_data["snippet"].get("liveStreamingDetails", {}).get("isVerified", False)
            
            # Find or create channel
            channel = db.query(Channel).filter(Channel.youtube_channel_id == youtube_channel_id).first()
            if not channel:
                channel = Channel(
                    owner_id=user.id,
                    youtube_channel_id=youtube_channel_id,
                    name=channel_name,
                    avatar_url=avatar_url,
                    subscribers=subscribers,
                    verified=is_verified
                )
                db.add(channel)
            else:
                # Update existing channel info
                channel.name = channel_name
                channel.avatar_url = avatar_url
                channel.subscribers = subscribers
                channel.verified = is_verified
            db.commit()
            db.refresh(channel)
        else:
            raise HTTPException(status_code=404, detail="No YouTube channel found for the authenticated user.")

    except Exception as e:
        print(f"Error fetching YouTube channel info: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error fetching YouTube channel info: {e}"})

    # Create a RedirectResponse explicitly
    redirect_response = RedirectResponse(FRONTEND_URL)
    # Set the cookie directly on the redirect_response object
    redirect_response.set_cookie(key="user_id", value=str(user.id), httponly=True, secure=False, samesite="Lax") # Added samesite="Lax" for broader compatibility

    return redirect_response