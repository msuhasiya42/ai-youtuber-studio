from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.models import Video, VideoRetentionCurve, VideoTrafficSource, ChannelDemographics
from datetime import datetime, timedelta
import statistics
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AdvancedPatternAnalyzer:
    """Data science-driven pattern analysis using YouTube Analytics metrics."""

    def __init__(self, db: Session, channel_id: int):
        self.db = db
        self.channel_id = channel_id

    def analyze_retention_by_duration(self) -> Dict:
        """
        Correlate video duration with retention rate.
        Find the sweet spot duration for maximum retention.
        """
        logger.info(f"Analyzing retention by duration for channel {self.channel_id}")

        videos = self.db.query(Video).filter(
            and_(
                Video.channel_id == self.channel_id,
                Video.average_view_percentage.isnot(None),
                Video.duration_seconds.isnot(None),
                Video.views > 100  # Minimum views for statistical significance
            )
        ).all()

        if not videos:
            logger.warning(f"No analytics data available for channel {self.channel_id}")
            return {'error': 'No analytics data available'}

        # Group by duration buckets
        duration_buckets = {
            '<3min': [],
            '3-6min': [],
            '6-10min': [],
            '10-15min': [],
            '15-20min': [],
            '>20min': []
        }

        for video in videos:
            minutes = video.duration_seconds / 60
            retention = video.average_view_percentage

            if minutes < 3:
                duration_buckets['<3min'].append(retention)
            elif minutes < 6:
                duration_buckets['3-6min'].append(retention)
            elif minutes < 10:
                duration_buckets['6-10min'].append(retention)
            elif minutes < 15:
                duration_buckets['10-15min'].append(retention)
            elif minutes < 20:
                duration_buckets['15-20min'].append(retention)
            else:
                duration_buckets['>20min'].append(retention)

        # Calculate averages
        results = {}
        for bucket, retentions in duration_buckets.items():
            if retentions:
                results[bucket] = {
                    'avg_retention': round(statistics.mean(retentions), 2),
                    'median_retention': round(statistics.median(retentions), 2),
                    'sample_size': len(retentions),
                    'std_dev': round(statistics.stdev(retentions), 2) if len(retentions) > 1 else 0
                }

        if not results:
            return {'error': 'Insufficient data for duration analysis'}

        # Find sweet spot
        sweet_spot = max(results.items(), key=lambda x: x[1]['avg_retention'])

        logger.info(f"Duration sweet spot: {sweet_spot[0]} with {sweet_spot[1]['avg_retention']}% retention")

        return {
            'duration_analysis': results,
            'sweet_spot': {
                'duration_range': sweet_spot[0],
                'avg_retention': sweet_spot[1]['avg_retention'],
                'sample_size': sweet_spot[1]['sample_size'],
                'confidence': 'high' if sweet_spot[1]['sample_size'] >= 5 else 'low'
            },
            'recommendation': self._generate_duration_recommendation(sweet_spot),
            'total_videos_analyzed': len(videos)
        }

    def analyze_hook_effectiveness(self) -> Dict:
        """
        Analyze first 30 seconds retention across videos.
        Correlate hook strength with overall performance.
        """
        logger.info(f"Analyzing hook effectiveness for channel {self.channel_id}")

        videos_with_retention = self.db.query(Video, VideoRetentionCurve).join(
            VideoRetentionCurve
        ).filter(
            Video.channel_id == self.channel_id,
            Video.views > 100
        ).all()

        if not videos_with_retention:
            logger.warning(f"No retention data available for channel {self.channel_id}")
            return {'error': 'No retention data available'}

        hook_performance = []

        for video, retention_curve in videos_with_retention:
            hook_performance.append({
                'video_id': video.id,
                'youtube_video_id': video.youtube_video_id,
                'title': video.title,
                'hook_retention': retention_curve.retention_at_30s or 0,
                'overall_retention': video.average_view_percentage or 0,
                'views': video.views,
                'engagement_rate': video.engagement_rate,
                'duration_minutes': round(video.duration_seconds / 60, 1)
            })

        # Sort by hook retention
        top_hooks = sorted(hook_performance, key=lambda x: x['hook_retention'], reverse=True)[:5]
        weak_hooks = sorted(hook_performance, key=lambda x: x['hook_retention'])[:5]

        # Calculate correlation
        avg_hook = statistics.mean([v['hook_retention'] for v in hook_performance])
        correlation_strength = self._calculate_correlation(
            [v['hook_retention'] for v in hook_performance],
            [v['overall_retention'] for v in hook_performance]
        )

        logger.info(f"Hook analysis complete - avg: {avg_hook:.1f}%, correlation: {correlation_strength:.2f}")

        return {
            'channel_avg_hook_retention': round(avg_hook, 2),
            'top_hooks': top_hooks,
            'weak_hooks': weak_hooks,
            'correlation_with_performance': round(correlation_strength, 3),
            'correlation_strength': self._interpret_correlation(correlation_strength),
            'insights': self._generate_hook_insights(avg_hook, correlation_strength),
            'total_videos_analyzed': len(hook_performance)
        }

    def analyze_traffic_source_performance(self) -> Dict:
        """
        Identify which traffic sources drive the most engagement.
        """
        logger.info(f"Analyzing traffic source performance for channel {self.channel_id}")

        # Get traffic source data with video metrics
        traffic_data = self.db.query(
            VideoTrafficSource.source_type,
            func.sum(VideoTrafficSource.views).label('total_views'),
            func.sum(VideoTrafficSource.watch_time_minutes).label('total_watch_time'),
            func.count(VideoTrafficSource.id).label('video_count')
        ).join(Video).filter(
            Video.channel_id == self.channel_id
        ).group_by(
            VideoTrafficSource.source_type
        ).all()

        if not traffic_data:
            logger.warning(f"No traffic source data available for channel {self.channel_id}")
            return {'error': 'No traffic source data available'}

        total_views = sum(row.total_views for row in traffic_data)

        source_performance = []
        for row in traffic_data:
            avg_watch_time = row.total_watch_time / row.total_views if row.total_views > 0 else 0
            source_performance.append({
                'source_type': self._format_source_name(row.source_type),
                'source_type_raw': row.source_type,
                'total_views': row.total_views,
                'percentage_of_traffic': round((row.total_views / total_views * 100), 2) if total_views > 0 else 0,
                'total_watch_time': row.total_watch_time,
                'avg_watch_time_per_view': round(avg_watch_time, 2),
                'videos_with_this_source': row.video_count
            })

        # Rank by quality (watch time per view)
        best_quality_source = max(source_performance, key=lambda x: x['avg_watch_time_per_view'])
        highest_volume_source = max(source_performance, key=lambda x: x['total_views'])

        logger.info(f"Traffic analysis complete - {len(source_performance)} sources analyzed")

        return {
            'traffic_source_breakdown': sorted(source_performance, key=lambda x: x['total_views'], reverse=True),
            'highest_volume_source': highest_volume_source,
            'best_quality_source': best_quality_source,
            'total_views_analyzed': total_views,
            'recommendations': self._generate_traffic_recommendations(source_performance)
        }

    def analyze_optimal_posting_time(self) -> Dict:
        """
        Analyze first 24-48 hour performance by day of week.
        """
        logger.info(f"Analyzing optimal posting time for channel {self.channel_id}")

        videos = self.db.query(Video).filter(
            and_(
                Video.channel_id == self.channel_id,
                Video.first_24h_views.isnot(None),
                Video.published_at.isnot(None),
                Video.views > 100
            )
        ).all()

        if not videos:
            logger.warning(f"Not enough data for time analysis for channel {self.channel_id}")
            return {'error': 'Not enough data for time analysis'}

        # Group by day of week
        day_performance = {i: [] for i in range(7)}  # 0=Monday, 6=Sunday

        for video in videos:
            day_of_week = video.published_at.weekday()
            day_performance[day_of_week].append({
                'first_24h_views': video.first_24h_views,
                'engagement_rate': video.engagement_rate,
                'retention': video.average_view_percentage or 0
            })

        # Calculate averages by day
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_analysis = []

        for day, performances in day_performance.items():
            if performances:
                day_analysis.append({
                    'day': day_names[day],
                    'day_number': day,
                    'avg_first_24h_views': round(statistics.mean([p['first_24h_views'] for p in performances]), 1),
                    'avg_engagement': round(statistics.mean([p['engagement_rate'] for p in performances]), 2),
                    'avg_retention': round(statistics.mean([p['retention'] for p in performances]), 2),
                    'sample_size': len(performances)
                })

        if not day_analysis:
            return {'error': 'Insufficient data for posting time analysis'}

        # Find best day
        best_day = max(day_analysis, key=lambda x: x['avg_first_24h_views'])

        logger.info(f"Best posting day: {best_day['day']} with {best_day['avg_first_24h_views']:.0f} avg views")

        return {
            'day_of_week_analysis': sorted(day_analysis, key=lambda x: x['day_number']),
            'best_posting_day': best_day,
            'confidence': 'high' if best_day['sample_size'] >= 3 else 'low',
            'total_videos_analyzed': len(videos)
        }

    def analyze_engagement_patterns(self) -> Dict:
        """
        Analyze engagement metrics (likes, comments, shares) patterns.
        """
        logger.info(f"Analyzing engagement patterns for channel {self.channel_id}")

        videos = self.db.query(Video).filter(
            and_(
                Video.channel_id == self.channel_id,
                Video.views > 100
            )
        ).all()

        if not videos:
            return {'error': 'No video data available'}

        engagement_data = []
        for video in videos:
            engagement_data.append({
                'video_id': video.id,
                'title': video.title,
                'views': video.views,
                'likes': video.likes,
                'comments': video.comments,
                'shares': video.shares,
                'engagement_rate': video.engagement_rate,
                'subscriber_conversion': video.subscriber_conversion_rate,
                'retention': video.average_view_percentage or 0
            })

        # Calculate channel benchmarks
        avg_engagement = statistics.mean([v['engagement_rate'] for v in engagement_data])
        avg_subscriber_conversion = statistics.mean([v['subscriber_conversion'] for v in engagement_data])

        # Find top performers
        top_engagement = sorted(engagement_data, key=lambda x: x['engagement_rate'], reverse=True)[:5]
        top_conversion = sorted(engagement_data, key=lambda x: x['subscriber_conversion'], reverse=True)[:5]

        logger.info(f"Engagement analysis complete - avg rate: {avg_engagement:.2f}%")

        return {
            'channel_avg_engagement_rate': round(avg_engagement, 2),
            'channel_avg_subscriber_conversion': round(avg_subscriber_conversion, 2),
            'top_engagement_videos': top_engagement,
            'top_conversion_videos': top_conversion,
            'engagement_benchmark': self._get_engagement_benchmark(avg_engagement),
            'total_videos_analyzed': len(videos)
        }

    def generate_content_recommendations(self) -> Dict:
        """
        Generate actionable recommendations based on all pattern analysis.
        """
        logger.info(f"Generating content recommendations for channel {self.channel_id}")

        # Run all analyses
        duration_analysis = self.analyze_retention_by_duration()
        hook_analysis = self.analyze_hook_effectiveness()
        traffic_analysis = self.analyze_traffic_source_performance()
        timing_analysis = self.analyze_optimal_posting_time()
        engagement_analysis = self.analyze_engagement_patterns()

        recommendations = []

        # Duration recommendation
        if 'sweet_spot' in duration_analysis:
            sweet_spot = duration_analysis['sweet_spot']
            recommendations.append({
                'category': 'video_length',
                'priority': 'high',
                'recommendation': f"Target {sweet_spot['duration_range']} videos - they have {sweet_spot['avg_retention']:.1f}% avg retention",
                'data_source': 'retention_correlation',
                'confidence': sweet_spot['confidence'],
                'impact': 'high'
            })

        # Hook recommendation
        if 'channel_avg_hook_retention' in hook_analysis:
            avg_hook = hook_analysis['channel_avg_hook_retention']
            if avg_hook < 70:
                recommendations.append({
                    'category': 'hook_strength',
                    'priority': 'critical',
                    'recommendation': f"Your hook retention is {avg_hook:.1f}%. Improve first 30 seconds to retain more viewers.",
                    'action_items': [
                        "Start with the most compelling moment",
                        "Add pattern interrupt within first 10 seconds",
                        "Clearly state value proposition upfront"
                    ],
                    'data_source': 'retention_analysis',
                    'confidence': 'high',
                    'impact': 'critical'
                })
            elif avg_hook > 85:
                recommendations.append({
                    'category': 'hook_strength',
                    'priority': 'low',
                    'recommendation': f"Excellent hook retention ({avg_hook:.1f}%) - maintain this standard!",
                    'data_source': 'retention_analysis',
                    'confidence': 'high',
                    'impact': 'maintain'
                })

        # Traffic source recommendation
        if 'best_quality_source' in traffic_analysis:
            best_source = traffic_analysis['best_quality_source']
            recommendations.append({
                'category': 'traffic_optimization',
                'priority': 'medium',
                'recommendation': f"{best_source['source_type']} viewers watch {best_source['avg_watch_time_per_view']:.1f} min/view - optimize for this source",
                'action_items': self._get_traffic_optimization_actions(best_source['source_type_raw']),
                'data_source': 'traffic_analysis',
                'confidence': 'medium',
                'impact': 'medium'
            })

        # Posting time recommendation
        if 'best_posting_day' in timing_analysis and timing_analysis.get('confidence') == 'high':
            best_day = timing_analysis['best_posting_day']
            recommendations.append({
                'category': 'publishing_schedule',
                'priority': 'low',
                'recommendation': f"Publish on {best_day['day']} - gets {best_day['avg_first_24h_views']:.0f} avg views in first 24h",
                'confidence': timing_analysis['confidence'],
                'data_source': 'timing_analysis',
                'impact': 'low'
            })

        # Engagement recommendation
        if 'channel_avg_engagement_rate' in engagement_analysis:
            avg_engagement = engagement_analysis['channel_avg_engagement_rate']
            if avg_engagement < 3:
                recommendations.append({
                    'category': 'engagement',
                    'priority': 'medium',
                    'recommendation': f"Engagement rate is {avg_engagement:.2f}% - add more CTAs and community interaction",
                    'action_items': [
                        "Ask questions in videos",
                        "Add comment prompts",
                        "Create controversial or discussion-worthy content"
                    ],
                    'data_source': 'engagement_analysis',
                    'confidence': 'medium',
                    'impact': 'medium'
                })

        logger.info(f"Generated {len(recommendations)} recommendations")

        return {
            'recommendations': sorted(recommendations, key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x['priority'], 4)),
            'last_updated': datetime.now().isoformat(),
            'analyses_performed': {
                'duration': not ('error' in duration_analysis),
                'hook': not ('error' in hook_analysis),
                'traffic': not ('error' in traffic_analysis),
                'timing': not ('error' in timing_analysis),
                'engagement': not ('error' in engagement_analysis)
            }
        }

    def get_comprehensive_insights(self) -> Dict:
        """
        Get all insights in one comprehensive report.
        """
        logger.info(f"Generating comprehensive insights for channel {self.channel_id}")

        return {
            'retention_by_duration': self.analyze_retention_by_duration(),
            'hook_effectiveness': self.analyze_hook_effectiveness(),
            'traffic_source_performance': self.analyze_traffic_source_performance(),
            'optimal_posting_time': self.analyze_optimal_posting_time(),
            'engagement_patterns': self.analyze_engagement_patterns(),
            'content_recommendations': self.generate_content_recommendations(),
            'generated_at': datetime.now().isoformat(),
            'channel_id': self.channel_id
        }

    # Helper methods

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) < 2 or len(y) < 2 or len(x) != len(y):
            return 0.0

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)
        sum_y2 = sum(yi ** 2 for yi in y)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def _generate_duration_recommendation(self, sweet_spot: Tuple) -> str:
        duration_range, metrics = sweet_spot
        return f"Aim for {duration_range} videos - they retain {metrics['avg_retention']:.1f}% of viewers on average (based on {metrics['sample_size']} videos)."

    def _generate_hook_insights(self, avg_hook: float, correlation: float) -> List[str]:
        insights = []

        if avg_hook < 70:
            insights.append("Hook retention is below industry average (70%) - focus on stronger openings")
        elif avg_hook > 85:
            insights.append("Excellent hook retention - your openings are very effective")

        if correlation > 0.7:
            insights.append("Strong correlation between hook and overall retention - first 30s are critical")
        elif correlation < 0.3:
            insights.append("Hook retention doesn't strongly predict overall retention - focus on mid-video engagement")

        return insights

    def _interpret_correlation(self, correlation: float) -> str:
        if abs(correlation) > 0.7:
            return "strong"
        elif abs(correlation) > 0.4:
            return "moderate"
        else:
            return "weak"

    def _generate_traffic_recommendations(self, source_performance: List[Dict]) -> List[str]:
        recommendations = []

        for source in source_performance:
            if source['source_type_raw'] == 'YT_SEARCH' and source['percentage_of_traffic'] < 20:
                recommendations.append(f"Optimize titles/descriptions for search - only getting {source['percentage_of_traffic']:.1f}% from search")
            elif source['source_type_raw'] == 'YT_SUGGESTED' and source['percentage_of_traffic'] > 50:
                recommendations.append("Great suggested video performance - algorithm loves your content")

        if not recommendations:
            recommendations.append("Traffic distribution looks healthy - maintain current strategy")

        return recommendations

    def _get_traffic_optimization_actions(self, source_type: str) -> List[str]:
        actions = {
            'YT_SEARCH': [
                "Research high-volume keywords in your niche",
                "Include target keywords in first 100 chars of description",
                "Use keyword-rich titles that match search intent"
            ],
            'YT_SUGGESTED': [
                "Maintain watch time above 50%",
                "Create content similar to top performers",
                "Use eye-catching thumbnails that match your brand"
            ],
            'EXT_URL': [
                "Leverage external promotion channels",
                "Share on relevant communities and forums",
                "Consider paid promotion for best-performing content"
            ],
            'ADVERTISING': [
                "Analyze which ads perform best",
                "Optimize ad targeting based on top demographics",
                "A/B test different ad creatives"
            ]
        }
        return actions.get(source_type, ["Optimize content for this traffic source"])

    def _format_source_name(self, source_type: str) -> str:
        """Format raw source type to human-readable name."""
        name_map = {
            'YT_SEARCH': 'YouTube Search',
            'YT_SUGGESTED': 'Suggested Videos',
            'YT_BROWSE': 'Browse Features',
            'YT_OTHER': 'Other YouTube',
            'EXT_URL': 'External Websites',
            'PLAYLIST': 'Playlists',
            'NOTIFICATION': 'Notifications',
            'ADVERTISING': 'Advertising',
            'NO_LINK_OTHER': 'Direct/Unknown'
        }
        return name_map.get(source_type, source_type)

    def _get_engagement_benchmark(self, avg_engagement: float) -> str:
        """Get engagement benchmark rating."""
        if avg_engagement > 8:
            return "excellent"
        elif avg_engagement > 5:
            return "above_average"
        elif avg_engagement > 3:
            return "average"
        else:
            return "below_average"
