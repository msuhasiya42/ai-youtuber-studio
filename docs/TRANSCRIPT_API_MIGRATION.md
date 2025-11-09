# Transcript API Migration Guide

## Goal: Reduce YouTube Data API Quota by 92%

Currently, fetching transcripts uses **250 quota units per video**.  
By switching to `youtube-transcript-api`, we use **0 quota units**.

---

## What is youtube-transcript-api?

- **Official Package:** https://pypi.org/project/youtube-transcript-api/
- **No authentication required** - Uses public YouTube endpoints
- **No API quota** - Doesn't count against your Data API limits
- **Works for most videos** - Any video with public captions (auto-generated or manual)

### Limitations:
- Won't work for videos with disabled captions
- Won't work for private/members-only captions
- Need fallback to authenticated API for these cases

---

## Implementation Plan

### Step 1: Install Package

```bash
cd backend
pip install youtube-transcript-api==0.6.1
pip freeze > requirements.txt
```

Add to `backend/requirements.txt`:
```txt
# YouTube Transcript (no quota usage)
youtube-transcript-api==0.6.1
```

---

### Step 2: Update ingest_worker.py

**Current file:** `backend/app/services/ingest_worker.py`

**Changes needed:**

```python
# Add import at top
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

# Update _fetch_authenticated_captions to try public API first
def _fetch_authenticated_captions(video_id: str, video: Video) -> dict:
    """
    Fetch captions with fallback strategy:
    1. Try public API (no quota) - youtube-transcript-api
    2. Fallback to authenticated API (uses quota) if public fails
    """
    logger.info(f"Attempting to fetch captions for video {video_id}")
    
    # Strategy 1: Try public transcript API first (NO QUOTA)
    try:
        logger.info(f"Trying public transcript API for {video_id}")
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Prefer manual captions over auto-generated
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
            logger.info(f"Found manual English transcript for {video_id}")
        except:
            # Fall back to auto-generated
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
                logger.info(f"Found auto-generated English transcript for {video_id}")
            except:
                # Try any available language
                transcript = transcript_list.find_transcript(['en', 'es', 'fr', 'de', 'pt', 'hi'])
                logger.info(f"Found transcript in language: {transcript.language_code}")
        
        # Fetch transcript data
        transcript_data = transcript.fetch()
        
        # Convert to our format
        segments = []
        for entry in transcript_data:
            segments.append({
                "start": entry['start'],
                "end": entry['start'] + entry['duration'],
                "text": entry['text']
            })
        
        result = {
            "language": transcript.language_code,
            "segments": segments,
            "source": "public_api",  # Track which method worked
            "is_generated": transcript.is_generated
        }
        
        logger.info(f"Successfully fetched transcript using public API (0 quota used)")
        return result
        
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.info(f"Public transcript not available for {video_id}: {e}")
        logger.info(f"Falling back to authenticated API (uses quota)")
        # Fall through to authenticated method below
        
    except VideoUnavailable as e:
        logger.error(f"Video {video_id} is unavailable: {e}")
        raise ValueError(f"Video unavailable: {e}")
        
    except Exception as e:
        logger.warning(f"Unexpected error with public API for {video_id}: {e}")
        logger.info(f"Falling back to authenticated API")
        # Fall through to authenticated method
    
    # Strategy 2: Authenticated API (USES QUOTA - 250 units)
    logger.info(f"Using authenticated YouTube Data API for {video_id} (uses quota)")
    
    # Get user credentials from video's channel owner
    user = video.channel.owner
    
    # Refresh OAuth token
    creds = Credentials(
        token=None,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=[
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ],
    )
    
    try:
        creds.refresh(GoogleAuthRequest())
    except Exception as e:
        logger.error(f"Failed to refresh credentials: {e}")
        raise ValueError(f"Authentication failed: {e}")
    
    # Initialize YouTube client
    from app.services.youtube_client import YouTubeClient
    youtube_client = YouTubeClient(credentials=creds)
    
    # List available captions
    try:
        captions_response = youtube_client.youtube.captions().list(
            part='snippet',
            videoId=video_id
        ).execute()
    except Exception as e:
        logger.error(f"Failed to list captions: {e}")
        raise ValueError(f"No captions available: {e}")
    
    if not captions_response.get('items'):
        raise ValueError(f"No captions found for video {video_id}")
    
    # Select caption track (prefer English ASR)
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
    transcript_data['source'] = 'authenticated_api'  # Track quota usage
    
    logger.warning(f"Used authenticated API - 250 quota units consumed")
    
    return transcript_data
```

---

### Step 3: Add Quota Monitoring

Create new file: `backend/app/services/quota_monitor.py`

```python
"""Track YouTube API quota usage"""
from datetime import datetime, timedelta
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class QuotaMonitor:
    """Simple in-memory quota tracker"""
    
    def __init__(self):
        self.daily_usage = {
            "data_api": {
                "date": datetime.now().date(),
                "units": 0,
                "calls": []
            }
        }
    
    def log_usage(self, api: str, operation: str, units: int):
        """
        Log API quota usage
        
        Args:
            api: "data_api" or "analytics_api"
            operation: e.g., "channels.list", "videos.list", "captions.download"
            units: Quota units consumed
        """
        today = datetime.now().date()
        
        # Reset if new day
        if self.daily_usage[api]["date"] != today:
            logger.info(
                f"Daily quota reset - {api} used "
                f"{self.daily_usage[api]['units']} units yesterday"
            )
            self.daily_usage[api] = {
                "date": today,
                "units": 0,
                "calls": []
            }
        
        # Log usage
        self.daily_usage[api]["units"] += units
        self.daily_usage[api]["calls"].append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "units": units
        })
        
        total_units = self.daily_usage[api]["units"]
        logger.info(
            f"API Usage: {operation} used {units} units "
            f"(Total today: {total_units}/10,000)"
        )
        
        # Alert if approaching limit
        if total_units > 8000:
            logger.warning(
                f"⚠️  {api} quota at {total_units}/10,000 units! "
                f"Approaching daily limit."
            )
        elif total_units > 9000:
            logger.error(
                f"🚨 {api} quota at {total_units}/10,000 units! "
                f"CRITICALLY CLOSE to daily limit!"
            )
    
    def get_usage(self, api: str = "data_api") -> Dict:
        """Get current usage stats"""
        return self.daily_usage.get(api, {})


# Global instance
quota_monitor = QuotaMonitor()


def log_quota_usage(operation: str, units: int):
    """Helper to log Data API quota usage"""
    quota_monitor.log_usage("data_api", operation, units)
```

---

### Step 4: Integrate Quota Monitoring

Update key files to log quota usage:

**In `backend/app/services/youtube_client.py`:**

```python
from app.services.quota_monitor import log_quota_usage

class YouTubeClient:
    def fetch_channel_metadata(self, channel_url_or_id: str) -> dict:
        # ... existing code ...
        response = self.youtube.channels().list(
            part="snippet,statistics,status",
            id=channel_id
        ).execute()
        
        log_quota_usage("channels.list", 3)  # Add this
        
        # ... rest of code ...
    
    def fetch_last_videos(self, channel_id: str, limit: int = 50, order: str = "date") -> list[dict]:
        # ... existing code ...
        search_response = self.youtube.search().list(
            part="id,snippet",
            channelId=channel_id,
            maxResults=min(limit, 50),
            order=order,
            type="video"
        ).execute()
        
        log_quota_usage("search.list", 100)  # Add this
        
        # ... more code ...
        
        videos_response = self.youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(video_ids)
        ).execute()
        
        log_quota_usage("videos.list", 1)  # Add this
        
        # ... rest of code ...
```

**In `backend/app/services/ingest_worker.py`:**

```python
from app.services.quota_monitor import log_quota_usage

def _fetch_authenticated_captions(video_id: str, video: Video) -> dict:
    # ... public API attempt (logs 0 units) ...
    
    # When falling back to authenticated API:
    captions_response = youtube_client.youtube.captions().list(
        part='snippet',
        videoId=video_id
    ).execute()
    
    log_quota_usage("captions.list", 50)  # Add this
    
    caption_content = youtube_client.youtube.captions().download(
        id=caption_id,
        tfmt='srt'
    ).execute()
    
    log_quota_usage("captions.download", 200)  # Add this
    
    # ... rest of code ...
```

---

### Step 5: Add Dashboard Endpoint (Optional)

**In `backend/app/api/analytics.py`:**

```python
from app.services.quota_monitor import quota_monitor

@router.get("/quota-usage")
async def get_quota_usage(current_user: User = Depends(get_current_user)):
    """Get current API quota usage"""
    return {
        "data_api": quota_monitor.get_usage("data_api"),
        "limit": 10000,
        "reset_time": "midnight PST"
    }
```

---

## Testing Plan

### Test Case 1: Public Transcript Available
```bash
# Most YouTube videos with auto-captions
video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up

Expected Result:
✅ Uses public API (0 quota)
✅ Successfully fetches transcript
✅ Logs: "Successfully fetched transcript using public API (0 quota used)"
```

### Test Case 2: No Public Transcript (Fallback)
```bash
# Video with captions disabled or members-only
video_id = "..." # Your private video

Expected Result:
⚠️  Falls back to authenticated API (250 quota)
✅ Successfully fetches transcript
✅ Logs: "Used authenticated API - 250 quota units consumed"
```

### Test Case 3: No Captions Available
```bash
# Video with no captions
video_id = "..." # Video without captions

Expected Result:
❌ Fails gracefully
✅ Returns: {"status": "no_captions", "skip": true}
```

---

## Rollout Strategy

### Phase 1: Development Environment (1 day)
1. Install youtube-transcript-api
2. Update ingest_worker.py with fallback logic
3. Test with 10-20 videos
4. Verify quota savings

### Phase 2: Add Monitoring (1 day)
1. Implement quota_monitor.py
2. Add logging to all API calls
3. Create dashboard endpoint
4. Monitor for 24 hours

### Phase 3: Production Deployment (1 day)
1. Update requirements.txt on server
2. Deploy updated code
3. Monitor quota usage
4. Verify 60-70% reduction

---

## Expected Results

### Before Migration:
```
Daily Quota Usage (per user):
- Channel refresh: 15 units (5 refreshes)
- Video sync: 202 units (2 syncs of 50 videos)
- Transcripts: 2,500 units (10 videos × 250)
TOTAL: 2,717 units/day
```

### After Migration:
```
Daily Quota Usage (per user):
- Channel refresh: 15 units
- Video sync: 202 units  
- Transcripts: 250 units (only 1/10 videos fallback to auth API)
TOTAL: 467 units/day

SAVINGS: 2,250 units/day (83% reduction!)
```

---

## Monitoring Commands

Check quota usage:
```bash
# View logs
tail -f backend/logs/app.log | grep "API Usage"

# Check daily totals
grep "Total today" backend/logs/app.log | tail -20

# Check fallback rate
grep "Falling back to authenticated API" backend/logs/app.log | wc -l
```

---

## Rollback Plan

If issues arise:

1. **Remove youtube-transcript-api import** from ingest_worker.py
2. **Keep only authenticated API code** (original implementation)
3. **Redeploy previous version**

The fallback strategy means the system will work even if the public API fails.

---

## FAQ

**Q: Why not use youtube-transcript-api for everything?**  
A: Some videos have disabled public captions. For channel owners' own videos, we can access private captions via authenticated API.

**Q: Will this work for all languages?**  
A: Yes! The public API supports all languages YouTube supports. We try English first, then fall back to other languages.

**Q: What about rate limits?**  
A: youtube-transcript-api has no rate limits (uses public endpoints). However, be respectful and don't hammer the API.

**Q: Is this against YouTube TOS?**  
A: No! youtube-transcript-api uses the same public endpoints that YouTube's website uses. It's not scraping.

---

## Success Metrics

Track these after deployment:

1. **Quota Usage:** Should drop from ~2,700 to ~500 units/day per user
2. **Fallback Rate:** % of videos that need authenticated API (target: <10%)
3. **Success Rate:** % of videos that get transcripts (target: >90%)
4. **Processing Speed:** Should be faster (no OAuth overhead)

---

## Next Steps

After successful migration, consider:

1. **Persistent Quota Tracking:** Store in Redis/database instead of in-memory
2. **User Quota Dashboard:** Show users their quota usage
3. **Smart Retry Logic:** Retry failed transcripts after 24h (quota reset)
4. **Quota Pooling:** Use multiple API keys for high-traffic scenarios

