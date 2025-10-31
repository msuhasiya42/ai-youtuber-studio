import os
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from urllib.parse import urlencode

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Change this to your deployed frontend URL in production
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
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
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
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
async def google_oauth_callback(request: Request, response: Response, code: str):
    """
    Handles Google OAuth redirect, exchanges code for token, fetches user/channel info, persists user/session.
    """
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    # Use the provided code in the redirect
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Error fetching token: {e}"})

    creds = flow.credentials
    # Optional: use creds.id_token for user identity
    # TODO: fetch channel info and store session/cookie as needed (simplified below)
    # Here: set dummy cookie (production = set secure httpOnly session with user id etc)
    response.set_cookie(key="session", value="dummy-session", httponly=True, secure=False)
    # Redirect to frontend dashboard (SPA will pick up session)
    return RedirectResponse(FRONTEND_URL)


