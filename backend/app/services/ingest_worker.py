"""
Ingest worker for fetching video captions/transcripts from YouTube API.
Replaces yt-dlp audio downloads with direct YouTube Caption API usage.
"""
from celery_worker import app as celery_app
import json
from app.services.storage_client import get_storage_client
from app.services.youtube_client import YouTubeClient
from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from app.models.models import Video

logger = get_logger(__name__)


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

        # Initialize YouTube client
        # If video exists, use owner's credentials; otherwise use service account
        youtube_client = None
        if video and video.channel and video.channel.owner:
            youtube_client = YouTubeClient(user=video.channel.owner)
        else:
            # Fallback: try to fetch using service account or public API
            logger.warning("No user credentials available, attempting public caption fetch")
            youtube_client = YouTubeClient()

        # Fetch captions list for the video
        logger.info(f"Fetching caption tracks for video: {video_id}")
        
        # Check if YouTube client is authenticated (captions API requires auth)
        if not youtube_client.youtube:
            logger.error(f"Cannot fetch captions for {video_id} - YouTube client not authenticated")
            return {
                "success": False,
                "status": "auth_required",
                "error": "YouTube Data API authentication required to fetch captions",
                "video_id": video_id
            }
        
        captions_response = youtube_client.youtube.captions().list(
            part="snippet",
            videoId=video_id
        ).execute()

        if not captions_response.get('items'):
            logger.warning(f"No captions available for video {video_id}")
            return {
                "success": False,
                "status": "no_captions",
                "error": "No captions available for this video",
                "video_id": video_id
            }

        # Prefer auto-generated English captions or first available
        caption_track = None
        for item in captions_response['items']:
            snippet = item['snippet']
            if snippet.get('language') == 'en':
                caption_track = item
                if snippet.get('trackKind') == 'asr':  # Auto-generated
                    break

        if not caption_track:
            caption_track = captions_response['items'][0]

        caption_id = caption_track['id']
        language = caption_track['snippet']['language']
        track_kind = caption_track['snippet'].get('trackKind', 'standard')

        logger.info(f"Downloading caption track: {caption_id} (language: {language}, kind: {track_kind})")

        # Download caption content
        caption_content = youtube_client.youtube.captions().download(
            id=caption_id,
            tfmt='srt'  # SubRip format
        ).execute()

        # Parse SRT to extract text and timestamps
        transcript_data = _parse_srt_to_transcript(caption_content, language)

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


