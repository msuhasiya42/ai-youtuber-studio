class YouTubeClient:
    def fetch_channel_metadata(self, channel_url_or_id: str) -> dict:
        # Placeholder: return mock metadata
        return {
            "channel_id": "mock_channel_id",
            "name": "Mock Channel",
            "avatar_url": "https://placehold.co/96x96",
            "subscribers": 123456,
            "verified": True,
        }

    def fetch_last_videos(self, channel_id: str, limit: int = 20) -> list[dict]:
        return [
            {
                "video_id": f"mockvid{i}",
                "title": f"Sample Video {i}",
                "thumbnail_url": "https://placehold.co/320x180",
                "duration_seconds": 480 + i,
            }
            for i in range(1, min(20, limit) + 1)
        ]


