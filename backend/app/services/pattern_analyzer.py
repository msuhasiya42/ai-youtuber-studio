"""
Pattern analyzer for identifying successful video patterns.
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.models import Video, Channel
from app.services.llm_provider import get_llm_provider
from app.services.vector_store import get_vector_store
import json
from collections import Counter
import re


class PatternAnalyzer:
    """Analyzes top-performing videos to extract success patterns"""

    def __init__(self):
        self.llm_provider = get_llm_provider()
        self.vector_store = get_vector_store()

    def get_top_videos(
        self,
        db: Session,
        channel_id: int,
        limit: int = 10,
        metric: str = "views"
    ) -> List[Video]:
        """
        Get top-performing videos from a channel.

        Args:
            db: Database session
            channel_id: Channel ID
            limit: Number of videos to return
            metric: Metric to sort by ('views', 'likes', or 'engagement')

        Returns:
            List of top videos
        """
        query = db.query(Video).filter(Video.channel_id == channel_id)

        if metric == "views":
            query = query.order_by(Video.views.desc())
        elif metric == "likes":
            query = query.order_by(Video.likes.desc())
        elif metric == "engagement":
            # Calculate engagement rate: (likes / views) * 100
            # Order by likes since we can't do complex calculations in SQLAlchemy easily
            query = query.order_by(Video.likes.desc())

        return query.limit(limit).all()

    def analyze_titles(self, videos: List[Video]) -> Dict:
        """
        Analyze title patterns in top videos.

        Args:
            videos: List of videos to analyze

        Returns:
            Title insights
        """
        titles = [v.title for v in videos]

        # Extract common words (excluding stop words)
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        all_words = []
        for title in titles:
            words = re.findall(r'\b\w+\b', title.lower())
            all_words.extend([w for w in words if w not in stop_words and len(w) > 2])

        word_freq = Counter(all_words).most_common(10)

        # Calculate average title length
        avg_length = sum(len(title) for title in titles) / len(titles) if titles else 0

        # Detect common patterns
        patterns = {
            "how_to": sum(1 for t in titles if "how to" in t.lower()),
            "number_based": sum(1 for t in titles if any(char.isdigit() for char in t)),
            "question_based": sum(1 for t in titles if "?" in t),
            "year_mentioned": sum(1 for t in titles if re.search(r'\b20\d{2}\b', t)),
        }

        return {
            "common_keywords": [{"word": word, "count": count} for word, count in word_freq],
            "average_length": round(avg_length, 1),
            "patterns": patterns,
            "sample_titles": titles[:5]
        }

    def analyze_duration(self, videos: List[Video]) -> Dict:
        """Analyze video duration patterns"""
        durations = [v.duration_seconds for v in videos if v.duration_seconds > 0]

        if not durations:
            return {"average_seconds": 0, "average_minutes": 0}

        avg_duration = sum(durations) / len(durations)

        return {
            "average_seconds": round(avg_duration, 1),
            "average_minutes": round(avg_duration / 60, 1),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "duration_range": f"{round(min(durations)/60, 1)}-{round(max(durations)/60, 1)} min"
        }

    def analyze_engagement(self, videos: List[Video]) -> Dict:
        """Analyze engagement metrics"""
        total_views = sum(v.views for v in videos)
        total_likes = sum(v.likes for v in videos)

        avg_views = total_views / len(videos) if videos else 0
        avg_likes = total_likes / len(videos) if videos else 0
        avg_engagement_rate = (total_likes / total_views * 100) if total_views > 0 else 0

        return {
            "average_views": round(avg_views),
            "average_likes": round(avg_likes),
            "engagement_rate": round(avg_engagement_rate, 2),
            "total_videos_analyzed": len(videos)
        }

    def extract_content_themes(self, videos: List[Video]) -> List[str]:
        """
        Use LLM to extract common content themes from top videos.

        Args:
            videos: List of videos

        Returns:
            List of content themes
        """
        # Create a summary of video titles and descriptions
        video_summaries = []
        for i, video in enumerate(videos[:5], 1):  # Analyze top 5
            video_summaries.append(f"{i}. {video.title}")

        prompt = f"""Analyze these top-performing video titles and identify 3-5 common content themes or topics:

{chr(10).join(video_summaries)}

Return ONLY a JSON array of themes, like this:
["theme1", "theme2", "theme3"]

Do not include any other text."""

        try:
            response = self.llm_provider.generate(prompt)
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                themes = json.loads(json_match.group())
                return themes[:5]  # Limit to 5 themes
        except Exception as e:
            print(f"Error extracting themes: {e}")

        # Fallback: return empty list
        return []

    def analyze_channel_patterns(
        self,
        db: Session,
        channel_id: int,
        top_n: int = 10
    ) -> Dict:
        """
        Comprehensive pattern analysis for a channel's top videos.

        Args:
            db: Database session
            channel_id: Channel ID
            top_n: Number of top videos to analyze

        Returns:
            Complete pattern analysis
        """
        # Get top videos
        top_videos = self.get_top_videos(db, channel_id, limit=top_n, metric="views")

        if not top_videos:
            return {
                "error": "No videos found for analysis",
                "channel_id": channel_id
            }

        # Analyze different aspects
        title_patterns = self.analyze_titles(top_videos)
        duration_patterns = self.analyze_duration(top_videos)
        engagement_patterns = self.analyze_engagement(top_videos)
        content_themes = self.extract_content_themes(top_videos)

        # Get channel info
        channel = db.query(Channel).filter(Channel.id == channel_id).first()

        return {
            "channel_name": channel.name if channel else "Unknown",
            "videos_analyzed": len(top_videos),
            "title_patterns": title_patterns,
            "duration_patterns": duration_patterns,
            "engagement_patterns": engagement_patterns,
            "content_themes": content_themes,
            "recommendations": self._generate_recommendations(
                title_patterns,
                duration_patterns,
                engagement_patterns,
                content_themes
            )
        }

    def _generate_recommendations(
        self,
        title_patterns: Dict,
        duration_patterns: Dict,
        engagement_patterns: Dict,
        themes: List[str]
    ) -> List[str]:
        """Generate actionable recommendations based on patterns"""
        recommendations = []

        # Title recommendations
        if title_patterns.get("patterns", {}).get("how_to", 0) > 2:
            recommendations.append("Consider using 'How to' format - it performs well for your audience")

        if title_patterns.get("patterns", {}).get("number_based", 0) > 3:
            recommendations.append("Number-based titles (e.g., '5 Ways to...') show strong performance")

        # Duration recommendations
        avg_minutes = duration_patterns.get("average_minutes", 0)
        if 5 <= avg_minutes <= 10:
            recommendations.append(f"Sweet spot: {round(avg_minutes, 1)} minute videos perform best")
        elif avg_minutes < 5:
            recommendations.append("Short-form content (under 5 min) resonates with your audience")
        else:
            recommendations.append("Long-form content (10+ min) drives engagement")

        # Engagement recommendations
        engagement_rate = engagement_patterns.get("engagement_rate", 0)
        if engagement_rate > 5:
            recommendations.append("High engagement rate! Keep doing what you're doing")
        elif engagement_rate < 2:
            recommendations.append("Consider adding stronger calls-to-action to boost engagement")

        # Theme recommendations
        if themes:
            top_theme = themes[0]
            recommendations.append(f"Top theme: '{top_theme}' - consider creating more content around this")

        return recommendations if recommendations else ["Continue analyzing performance to identify patterns"]


# Singleton instance
_pattern_analyzer = None


def get_pattern_analyzer() -> PatternAnalyzer:
    """Get or create pattern analyzer singleton"""
    global _pattern_analyzer
    if _pattern_analyzer is None:
        _pattern_analyzer = PatternAnalyzer()
    return _pattern_analyzer
