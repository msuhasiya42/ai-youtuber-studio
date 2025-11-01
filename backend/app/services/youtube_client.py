from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime
import isodate
from typing import Optional


class YouTubeClient:
    """Client for interacting with YouTube Data API v3"""

    def __init__(self, credentials: Optional[Credentials] = None):
        """
        Initialize YouTube client with optional credentials.
        If credentials are provided, API quota will be charged to the authenticated user.
        """
        self.credentials = credentials
        self.youtube = build("youtube", "v3", credentials=credentials) if credentials else None

    def fetch_channel_metadata(self, channel_url_or_id: str) -> dict:
        """
        Fetch channel metadata from YouTube Data API.

        Args:
            channel_url_or_id: YouTube channel ID or URL

        Returns:
            dict with channel_id, name, avatar_url, subscribers, verified
        """
        if not self.youtube:
            raise ValueError("YouTubeClient not initialized with credentials")

        # Extract channel ID if URL is provided
        channel_id = self._extract_channel_id(channel_url_or_id)

        response = self.youtube.channels().list(
            part="snippet,statistics,status",
            id=channel_id
        ).execute()

        if not response.get("items"):
            raise ValueError(f"Channel not found: {channel_id}")

        channel_data = response["items"][0]

        return {
            "channel_id": channel_id,
            "name": channel_data["snippet"]["title"],
            "avatar_url": channel_data["snippet"]["thumbnails"]["default"]["url"],
            "subscribers": int(channel_data["statistics"].get("subscriberCount", 0)),
            "verified": channel_data.get("status", {}).get("isLinked", False),
            "total_views": int(channel_data["statistics"].get("viewCount", 0)),
        }

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
            raise ValueError("YouTubeClient not initialized with credentials")

        # Step 1: Search for videos from the channel
        search_response = self.youtube.search().list(
            part="id,snippet",
            channelId=channel_id,
            maxResults=min(limit, 50),
            order=order,
            type="video"
        ).execute()

        if not search_response.get("items"):
            return []

        # Extract video IDs
        video_ids = [item["id"]["videoId"] for item in search_response["items"]]

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

        return videos

    def _extract_channel_id(self, channel_url_or_id: str) -> str:
        """Extract channel ID from URL or return as-is if already an ID"""
        # If it's already a channel ID (starts with UC), return it
        if channel_url_or_id.startswith("UC") and len(channel_url_or_id) == 24:
            return channel_url_or_id

        # TODO: Handle URL parsing if needed
        # For now, assume it's already an ID
        return channel_url_or_id


