from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime
import isodate
from typing import Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class YouTubeClient:
    """Client for interacting with YouTube Data API v3"""

    def __init__(self, credentials: Optional[Credentials] = None):
        """
        Initialize YouTube client with optional credentials.
        If credentials are provided, API quota will be charged to the authenticated user.
        """
        self.credentials = credentials
        self.youtube = build("youtube", "v3", credentials=credentials) if credentials else None
        logger.info(f"YouTubeClient initialized (authenticated: {credentials is not None})")

    def fetch_channel_metadata(self, channel_url_or_id: str) -> dict:
        """
        Fetch channel metadata from YouTube Data API.

        Args:
            channel_url_or_id: YouTube channel ID or URL

        Returns:
            dict with channel_id, name, avatar_url, subscribers, verified
        """
        if not self.youtube:
            logger.error("Attempted to fetch channel metadata without credentials")
            raise ValueError("YouTubeClient not initialized with credentials")

        # Extract channel ID if URL is provided
        channel_id = self._extract_channel_id(channel_url_or_id)
        logger.info(f"Fetching channel metadata for: {channel_id}")

        try:
            response = self.youtube.channels().list(
                part="snippet,statistics,status",
                id=channel_id
            ).execute()

            if not response.get("items"):
                logger.warning(f"Channel not found: {channel_id}")
                raise ValueError(f"Channel not found: {channel_id}")

            channel_data = response["items"][0]
            channel_name = channel_data["snippet"]["title"]
            subscribers = int(channel_data["statistics"].get("subscriberCount", 0))
            total_views = int(channel_data["statistics"].get("viewCount", 0))

            logger.info(
                f"Channel metadata fetched - name: {channel_name}, "
                f"subscribers: {subscribers:,}, views: {total_views:,}"
            )

            return {
                "channel_id": channel_id,
                "name": channel_name,
                "avatar_url": channel_data["snippet"]["thumbnails"]["default"]["url"],
                "subscribers": subscribers,
                "verified": channel_data.get("status", {}).get("isLinked", False),
                "total_views": total_views,
            }
        except Exception as e:
            logger.error(f"Error fetching channel metadata for {channel_id}: {e}", exc_info=True)
            raise

    def fetch_last_videos(self, channel_id: str, limit: int = 50, order: str = "date") -> list[dict]:
        """
        Fetch recent videos from a YouTube channel.

        Args:
            channel_id: YouTube channel ID
            limit: Maximum number of videos to fetch (default: 50, max: 50 per request)
            order: Sort order - 'date', 'viewCount', 'rating' (default: 'date')

        Returns:
            List of video dictionaries with metadata
        """
        if not self.youtube:
            logger.error("Attempted to fetch videos without credentials")
            raise ValueError("YouTubeClient not initialized with credentials")

        logger.info(f"Fetching videos for channel {channel_id} (limit: {limit}, order: {order})")

        try:
            # Step 1: Search for videos from the channel
            search_response = self.youtube.search().list(
                part="id,snippet",
                channelId=channel_id,
                maxResults=min(limit, 50),
                order=order,
                type="video"
            ).execute()

            if not search_response.get("items"):
                logger.info(f"No videos found for channel {channel_id}")
                return []

            # Extract video IDs
            video_ids = [item["id"]["videoId"] for item in search_response["items"]]
            logger.debug(f"Found {len(video_ids)} video IDs, fetching detailed metadata")

            # Step 2: Get detailed video statistics
            videos_response = self.youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=",".join(video_ids)
            ).execute()

            videos = []
            for video in videos_response.get("items", []):
                video_id = video["id"]
                snippet = video["snippet"]
                stats = video.get("statistics", {})
                content_details = video.get("contentDetails", {})

                # Parse ISO 8601 duration
                duration_iso = content_details.get("duration", "PT0S")
                duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())

                # Parse published date
                published_at = snippet.get("publishedAt")
                if published_at:
                    published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

                videos.append({
                    "video_id": video_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "thumbnail_url": snippet["thumbnails"]["medium"]["url"],
                    "duration_seconds": duration_seconds,
                    "published_at": published_at,
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                })

            total_views = sum(v["views"] for v in videos)
            logger.info(
                f"Fetched {len(videos)} videos for channel {channel_id} - "
                f"Total views: {total_views:,}"
            )

            return videos
        except Exception as e:
            logger.error(f"Error fetching videos for channel {channel_id}: {e}", exc_info=True)
            raise

    def _extract_channel_id(self, channel_url_or_id: str) -> str:
        """Extract channel ID from URL or return as-is if already an ID"""
        # If it's already a channel ID (starts with UC), return it
        if channel_url_or_id.startswith("UC") and len(channel_url_or_id) == 24:
            return channel_url_or_id

        # TODO: Handle URL parsing if needed
        # For now, assume it's already an ID
        return channel_url_or_id


