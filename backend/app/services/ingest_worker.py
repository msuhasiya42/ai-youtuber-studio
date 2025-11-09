"""
Ingest worker for fetching video captions/transcripts from YouTube Data API.
Requires authenticated user credentials via OAuth.
"""
from celery_worker import app as celery_app
import json
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from app.services.storage_client import get_storage_client
from app.services.youtube_client import YouTubeClient
from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from app.models.models import Video

logger = get_logger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


@celery_app.task
def fetch_video_captions(video_id: str, db_video_id: int = None) -> dict:
    """
    Fetch captions/transcript directly from YouTube using YouTube Data API v3.

    Args:
        video_id: YouTube video ID (not full URL)
        db_video_id: Optional database video ID for updating record

    Returns:
        dict with status and transcript_s3_key
    """
    logger.info(f"Fetching captions for video: {video_id}")
    storage_client = get_storage_client()
    db = SessionLocal()

    try:
        # Get video from database to access owner's YouTube client
        video = None
        if db_video_id:
            video = db.query(Video).filter(Video.id == db_video_id).first()
            if not video:
                logger.warning(f"Video {db_video_id} not found in database")

        # Require authenticated user credentials
        if not video or not video.channel or not video.channel.owner:
            logger.warning(f"No user credentials available for video {video_id}, skipping caption fetch")
            return {
                "success": False,
                "status": "no_auth",
                "error": "User authentication required",
                "video_id": video_id,
                "skip": True  # Indicates this should be skipped silently
            }

        # Fetch captions using authenticated YouTube Data API
        logger.info(f"Fetching captions for video {video_id} using authenticated API")
        try:
            transcript_data = _fetch_authenticated_captions(video_id, video)
            language = transcript_data.get("language", "en")
            track_kind = "authenticated"
            logger.info(f"Successfully fetched captions (language: {language})")
        except ValueError as e:
            # No captions available - skip silently with warning
            logger.warning(f"No captions available for video {video_id}: {e}")
            return {
                "success": False,
                "status": "no_captions",
                "error": str(e),
                "video_id": video_id,
                "skip": True  # Indicates this should be skipped silently
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching captions for {video_id}: {e}")
            return {
                "success": False,
                "status": "error",
                "error": f"Caption fetch failed: {str(e)}",
                "video_id": video_id
            }

        # Upload transcript to storage
        transcript_s3_key = f"transcripts/{video_id}.json"
        transcript_json = json.dumps(transcript_data, indent=2).encode('utf-8')
        transcript_size_kb = len(transcript_json) / 1024

        logger.info(f"Uploading transcript to storage: {transcript_s3_key} ({transcript_size_kb:.2f} KB)")
        storage_client.upload_bytes(
            data=transcript_json,
            object_name=transcript_s3_key,
            content_type="application/json"
        )
        logger.info(f"Transcript uploaded successfully: {transcript_s3_key}")

        # Update video record if available
        if video:
            video.transcript_s3_key = transcript_s3_key
            db.add(video)
            db.commit()
            logger.info(f"Updated video {db_video_id} with transcript key")

        return {
            "success": True,
            "status": "success",
            "transcript_s3_key": transcript_s3_key,
            "video_id": video_id,
            "language": language,
            "track_kind": track_kind,
            "text_length": len(transcript_data['text']),
            "segments_count": len(transcript_data['segments'])
        }

    except Exception as e:
        logger.error(f"Error fetching captions for {video_id}: {e}", exc_info=True)
        return {
            "success": False,
            "status": "error",
            "error": str(e),
            "video_id": video_id
        }
    finally:
        db.close()


def _fetch_authenticated_captions(video_id: str, video: Video) -> dict:
    """
    Fetch captions using authenticated YouTube Data API.
    Requires OAuth user credentials.
    
    Args:
        video_id: YouTube video ID
        video: Video model instance with channel and owner
        
    Returns:
        dict with text, language, duration, segments, and source
        
    Raises:
        ValueError: If no captions are available or authentication fails
    """
    user = video.channel.owner
    
    # Create credentials from user's refresh token
    if not user or not user.google_refresh_token:
        raise ValueError("User authentication required - no refresh token")
    
    creds = Credentials(
        token=None,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl",  # Required for captions access
            "https://www.googleapis.com/auth/userinfo.email",
            "openid"
        ],
    )
    
    # Refresh the token
    creds.refresh(GoogleAuthRequest())
    
    # Initialize YouTube client with credentials
    youtube_client = YouTubeClient(credentials=creds)
    
    if not youtube_client.youtube:
        raise ValueError("YouTube client not authenticated")
    
    # Fetch captions list
    captions_response = youtube_client.youtube.captions().list(
        part="snippet",
        videoId=video_id
    ).execute()
    
    if not captions_response.get('items'):
        raise ValueError("No captions available for this video")
    
    # Prefer English auto-generated or first available
    caption_track = None
    for item in captions_response['items']:
        snippet = item['snippet']
        if snippet.get('language') == 'en':
            caption_track = item
            if snippet.get('trackKind') == 'asr':
                break
    
    if not caption_track:
        caption_track = captions_response['items'][0]
    
    caption_id = caption_track['id']
    language = caption_track['snippet']['language']
    
    # Download caption content in SRT format
    caption_content = youtube_client.youtube.captions().download(
        id=caption_id,
        tfmt='srt'
    ).execute()
    
    # Decode bytes to string if needed
    if isinstance(caption_content, bytes):
        caption_content = caption_content.decode('utf-8')
    
    # Parse SRT to our format
    transcript_data = _parse_srt_to_transcript(caption_content, language)
    transcript_data['source'] = 'youtube_data_api'
    
    return transcript_data


def _parse_srt_to_transcript(srt_content: str, language: str) -> dict:
    """
    Parse SRT (SubRip) format captions into transcript data structure.

    Args:
        srt_content: Raw SRT content string
        language: Language code

    Returns:
        dict with text, language, duration, and segments
    """
    import re

    segments = []
    full_text_parts = []

    # Split SRT into blocks (separated by double newlines)
    blocks = srt_content.strip().split('\n\n')

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        # Parse timestamp line (format: 00:00:01,234 --> 00:00:05,678)
        timestamp_line = lines[1]
        timestamp_match = re.match(
            r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
            timestamp_line
        )

        if not timestamp_match:
            continue

        # Convert timestamp to seconds
        start_h, start_m, start_s, start_ms = map(int, timestamp_match.groups()[:4])
        end_h, end_m, end_s, end_ms = map(int, timestamp_match.groups()[4:])

        start_seconds = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
        end_seconds = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000

        # Get text (lines after timestamp)
        text = ' '.join(lines[2:]).strip()
        full_text_parts.append(text)

        segments.append({
            "start": round(start_seconds, 3),
            "end": round(end_seconds, 3),
            "text": text
        })

    # Calculate total duration
    duration = segments[-1]['end'] if segments else 0

    return {
        "text": ' '.join(full_text_parts),
        "language": language,
        "duration": duration,
        "segments": segments,
        "source": "youtube_captions"
    }


