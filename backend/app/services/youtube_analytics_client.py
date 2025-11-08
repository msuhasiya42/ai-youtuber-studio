from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class YouTubeAnalyticsClient:
    """Enhanced YouTube Analytics API client for comprehensive metrics"""

    def __init__(self, credentials: Credentials):
        """
        Initialize YouTube Analytics client with OAuth credentials.

        Args:
            credentials: Google OAuth2 credentials with yt-analytics.readonly scope
        """
        if not credentials:
            raise ValueError("Credentials are required for YouTube Analytics API")

        self.credentials = credentials
        self.analytics = build('youtubeAnalytics', 'v2', credentials=credentials)
        self.data_api = build('youtube', 'v3', credentials=credentials)
        logger.info("YouTubeAnalyticsClient initialized successfully")

    def fetch_video_analytics(
        self,
        video_id: str,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        Fetch comprehensive analytics for a single video.

        Args:
            video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format

        Returns:
            Dict with all available metrics
        """
        logger.info(f"Fetching analytics for video {video_id} ({start_date} to {end_date})")

        try:
            response = self.analytics.reports().query(
                ids='channel==MINE',  # Uses authenticated channel
                startDate=start_date,
                endDate=end_date,
                metrics=','.join([
                    'views',
                    'likes',
                    'comments',
                    'shares',
                    'estimatedMinutesWatched',
                    'averageViewDuration',
                    'averageViewPercentage',
                    'subscribersGained',
                    'subscribersLost',
                    'videosAddedToPlaylists',
                    'videosRemovedFromPlaylists',
                ]),
                dimensions='video',
                filters=f'video=={video_id}',
                sort='-views'
            ).execute()

            if not response.get('rows'):
                logger.warning(f"No analytics data available for video {video_id}")
                return {}

            # Parse response
            headers = [h['name'] for h in response['columnHeaders']]
            row = response['rows'][0]  # Single video

            metrics = dict(zip(headers, row))
            logger.info(f"Successfully fetched {len(metrics)} metrics for video {video_id}")

            return metrics

        except Exception as e:
            logger.error(f"Error fetching analytics for {video_id}: {e}", exc_info=True)
            return {}

    def fetch_retention_curve(self, video_id: str) -> Optional[List[Dict]]:
        """
        Fetch audience retention curve (absolute retention).

        Note: This API requires special access and may not be available for all channels.

        Args:
            video_id: YouTube video ID

        Returns:
            List of {elapsed_ratio, retention_ratio} or None if unavailable
        """
        logger.info(f"Fetching retention curve for video {video_id}")

        try:
            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate='2000-01-01',  # All time
                endDate=datetime.now().strftime('%Y-%m-%d'),
                metrics='audienceWatchRatio,relativeRetentionPerformance',
                dimensions='elapsedVideoTimeRatio',
                filters=f'video=={video_id}',
                maxResults=100  # Get detailed curve
            ).execute()

            if not response.get('rows'):
                logger.info(f"Retention curve not available for video {video_id}")
                return None

            headers = [h['name'] for h in response['columnHeaders']]
            retention_points = []

            for row in response['rows']:
                data = dict(zip(headers, row))
                retention_points.append({
                    'elapsed_ratio': float(data['elapsedVideoTimeRatio']),
                    'retention_ratio': float(data['audienceWatchRatio']),
                })

            logger.info(f"Fetched retention curve with {len(retention_points)} data points for video {video_id}")
            return retention_points

        except Exception as e:
            logger.warning(f"Retention curve not available for {video_id}: {e}")
            return None

    def fetch_traffic_sources(
        self,
        video_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        Fetch traffic source breakdown for a video.

        Args:
            video_id: YouTube video ID
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format

        Returns:
            List of {source_type, views, watch_time_minutes, percentage}
        """
        logger.info(f"Fetching traffic sources for video {video_id}")

        try:
            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='views,estimatedMinutesWatched',
                dimensions='insightTrafficSourceType',
                filters=f'video=={video_id}',
                sort='-views'
            ).execute()

            if not response.get('rows'):
                logger.info(f"No traffic source data for video {video_id}")
                return []

            traffic_sources = []
            total_views = sum(row[1] for row in response['rows'])

            for row in response['rows']:
                source_type = row[0]
                views = row[1]
                watch_time = row[2]

                traffic_sources.append({
                    'source_type': source_type,
                    'views': views,
                    'watch_time_minutes': watch_time,
                    'percentage': (views / total_views * 100) if total_views > 0 else 0
                })

            logger.info(f"Fetched {len(traffic_sources)} traffic sources for video {video_id}")
            return traffic_sources

        except Exception as e:
            logger.error(f"Error fetching traffic sources for {video_id}: {e}", exc_info=True)
            return []

    def fetch_batch_video_analytics(
        self,
        video_ids: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, Dict]:
        """
        Fetch analytics for multiple videos in a single request.
        YouTube Analytics API allows filtering by multiple videos.

        Args:
            video_ids: List of YouTube video IDs (max 200)
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format

        Returns:
            Dict mapping video_id -> metrics
        """
        if not video_ids:
            return {}

        # Limit to 200 videos per request
        video_ids = video_ids[:200]

        logger.info(f"Fetching batch analytics for {len(video_ids)} videos")

        try:
            # Join video IDs with comma for OR filter
            video_filter = ','.join(video_ids)

            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics=','.join([
                    'views',
                    'likes',
                    'comments',
                    'shares',
                    'estimatedMinutesWatched',
                    'averageViewDuration',
                    'averageViewPercentage',
                    'subscribersGained',
                ]),
                dimensions='video',
                filters=f'video=={video_filter}',
                maxResults=200
            ).execute()

            if not response.get('rows'):
                logger.warning(f"No analytics data for batch request")
                return {}

            headers = [h['name'] for h in response['columnHeaders']]
            results = {}

            for row in response['rows']:
                data = dict(zip(headers, row))
                video_id = data.pop('video')
                results[video_id] = data

            logger.info(f"Successfully fetched analytics for {len(results)} videos")
            return results

        except Exception as e:
            logger.error(f"Error fetching batch analytics: {e}", exc_info=True)
            return {}

    def fetch_channel_demographics(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, List[Dict]]:
        """
        Fetch audience demographics (age, gender, geography).

        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format

        Returns:
            {
                'age_groups': [{group, percentage}, ...],
                'genders': [{gender, percentage}, ...],
                'countries': [{country, percentage, views}, ...]
            }
        """
        logger.info(f"Fetching channel demographics ({start_date} to {end_date})")

        demographics = {
            'age_groups': [],
            'genders': [],
            'countries': []
        }

        # Age groups
        try:
            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='viewerPercentage',
                dimensions='ageGroup',
                sort='-viewerPercentage'
            ).execute()

            if response.get('rows'):
                for row in response['rows']:
                    demographics['age_groups'].append({
                        'group': row[0],
                        'percentage': row[1]
                    })
                logger.info(f"Fetched {len(demographics['age_groups'])} age groups")
        except Exception as e:
            logger.warning(f"Age demographics not available: {e}")

        # Gender
        try:
            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='viewerPercentage',
                dimensions='gender',
                sort='-viewerPercentage'
            ).execute()

            if response.get('rows'):
                for row in response['rows']:
                    demographics['genders'].append({
                        'gender': row[0],
                        'percentage': row[1]
                    })
                logger.info(f"Fetched {len(demographics['genders'])} gender demographics")
        except Exception as e:
            logger.warning(f"Gender demographics not available: {e}")

        # Top 10 countries
        try:
            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='views',
                dimensions='country',
                sort='-views',
                maxResults=10
            ).execute()

            if response.get('rows'):
                total_views = sum(row[1] for row in response['rows'])
                for row in response['rows']:
                    demographics['countries'].append({
                        'country': row[0],
                        'views': row[1],
                        'percentage': (row[1] / total_views * 100) if total_views > 0 else 0
                    })
                logger.info(f"Fetched top {len(demographics['countries'])} countries")
        except Exception as e:
            logger.warning(f"Geography demographics not available: {e}")

        return demographics

    def fetch_first_24h_performance(
        self,
        video_id: str,
        published_date: datetime
    ) -> Optional[int]:
        """
        Fetch first 24-hour view count for a video.

        Args:
            video_id: YouTube video ID
            published_date: Video publication datetime

        Returns:
            View count in first 24 hours, or None if unavailable
        """
        start_date = published_date.strftime('%Y-%m-%d')
        end_date = (published_date + timedelta(days=1)).strftime('%Y-%m-%d')

        logger.info(f"Fetching first 24h performance for video {video_id}")

        try:
            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='views',
                filters=f'video=={video_id}'
            ).execute()

            if response.get('rows'):
                first_24h_views = response['rows'][0][0]
                logger.info(f"Video {video_id} got {first_24h_views} views in first 24h")
                return first_24h_views

            return None

        except Exception as e:
            logger.warning(f"First 24h data not available for {video_id}: {e}")
            return None

    def fetch_channel_watch_hours(
        self,
        start_date: str = '2000-01-01',
        end_date: Optional[str] = None
    ) -> float:
        """
        Fetch total watch hours for a channel (all-time or date range).

        Args:
            start_date: YYYY-MM-DD format (default: all time)
            end_date: YYYY-MM-DD format (default: today)

        Returns:
            Total watch hours
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"Fetching channel watch hours ({start_date} to {end_date})")

        try:
            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='estimatedMinutesWatched'
            ).execute()

            if response.get('rows'):
                total_minutes = response['rows'][0][0]
                total_hours = total_minutes / 60
                logger.info(f"Channel has {total_hours:.2f} watch hours")
                return total_hours

            return 0.0

        except Exception as e:
            logger.error(f"Error fetching watch hours: {e}", exc_info=True)
            return 0.0
