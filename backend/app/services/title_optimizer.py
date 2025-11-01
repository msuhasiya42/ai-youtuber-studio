"""
Title optimizer service for generating and scoring video titles.
"""
from typing import List, Dict
from app.services.llm_provider import get_llm_provider
from app.services.pattern_analyzer import get_pattern_analyzer
from sqlalchemy.orm import Session
import json
import re


class TitleOptimizer:
    """Generates and optimizes video titles based on performance data"""

    def __init__(self):
        self.llm_provider = get_llm_provider()
        self.pattern_analyzer = get_pattern_analyzer()

    def score_title(self, title: str, patterns: Dict) -> Dict:
        """
        Score a title based on known performance patterns.

        Args:
            title: Title to score
            patterns: Title patterns from pattern analyzer

        Returns:
            Score and breakdown
        """
        score = 50  # Base score
        factors = []

        # Length scoring (optimal: 50-60 characters)
        length = len(title)
        if 50 <= length <= 60:
            score += 15
            factors.append({"factor": "Optimal length", "points": 15})
        elif 40 <= length < 50 or 60 < length <= 70:
            score += 5
            factors.append({"factor": "Good length", "points": 5})
        else:
            score -= 5
            factors.append({"factor": "Suboptimal length", "points": -5})

        # Keyword presence
        common_keywords = patterns.get("common_keywords", [])
        if common_keywords:
            title_lower = title.lower()
            keyword_matches = sum(1 for kw in common_keywords[:5] if kw["word"] in title_lower)
            keyword_score = keyword_matches * 5
            score += keyword_score
            if keyword_score > 0:
                factors.append({"factor": f"Contains {keyword_matches} trending keywords", "points": keyword_score})

        # Pattern matching
        title_patterns = patterns.get("patterns", {})

        if "how to" in title.lower() and title_patterns.get("how_to", 0) > 2:
            score += 10
            factors.append({"factor": "'How to' format (proven performer)", "points": 10})

        if any(char.isdigit() for char in title) and title_patterns.get("number_based", 0) > 3:
            score += 8
            factors.append({"factor": "Number-based (increases CTR)", "points": 8})

        if "?" in title and title_patterns.get("question_based", 0) > 2:
            score += 7
            factors.append({"factor": "Question format (curiosity driver)", "points": 7})

        # Year mention
        if re.search(r'\b20\d{2}\b', title):
            score += 5
            factors.append({"factor": "Includes current/relevant year", "points": 5})

        # Emotional triggers
        emotional_words = ["secret", "amazing", "shocking", "ultimate", "best", "worst", "never", "always"]
        if any(word in title.lower() for word in emotional_words):
            score += 6
            factors.append({"factor": "Emotional trigger word", "points": 6})

        # Cap at 100
        score = min(score, 100)

        return {
            "score": score,
            "predicted_ctr_range": self._score_to_ctr(score),
            "factors": factors,
            "grade": self._score_to_grade(score)
        }

    def _score_to_ctr(self, score: int) -> str:
        """Convert score to estimated CTR range"""
        if score >= 85:
            return "8-12%"
        elif score >= 70:
            return "6-8%"
        elif score >= 55:
            return "4-6%"
        else:
            return "2-4%"

    def _score_to_grade(self, score: int) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        else:
            return "D"

    def generate_title_variations(
        self,
        topic: str,
        db: Session,
        channel_id: int,
        count: int = 5
    ) -> List[Dict]:
        """
        Generate multiple title variations for a topic and score them.

        Args:
            topic: Video topic
            db: Database session
            channel_id: Channel ID for pattern analysis
            count: Number of variations to generate

        Returns:
            List of titles with scores
        """
        # Get channel patterns
        patterns = self.pattern_analyzer.analyze_channel_patterns(db, channel_id, top_n=10)

        # Extract pattern insights for prompt
        common_keywords = [kw["word"] for kw in patterns.get("title_patterns", {}).get("common_keywords", [])[:5]]
        successful_titles = patterns.get("title_patterns", {}).get("sample_titles", [])

        prompt = f"""You are a YouTube title optimization expert. Generate {count} different title variations for this video topic.

TOPIC: {topic}

SUCCESSFUL TITLE PATTERNS FROM THIS CHANNEL:
{chr(10).join(f"- {title}" for title in successful_titles[:3])}

TRENDING KEYWORDS: {", ".join(common_keywords)}

REQUIREMENTS:
- Each title should be 50-60 characters
- Use proven patterns (how-to, numbers, questions, emotional triggers)
- Include relevant keywords
- Make them click-worthy but not clickbait
- Vary the style (some with numbers, some with questions, etc.)

Return ONLY a JSON array of titles:
["Title 1", "Title 2", "Title 3", ...]

Generate {count} titles now:"""

        try:
            response = self.llm_provider.generate(prompt)

            # Extract JSON array from response
            json_start = response.find("[")
            json_end = response.rfind("]") + 1

            if json_start != -1 and json_end > json_start:
                titles = json.loads(response[json_start:json_end])

                # Score each title
                scored_titles = []
                for title in titles[:count]:
                    score_data = self.score_title(title, patterns["title_patterns"])
                    scored_titles.append({
                        "title": title,
                        "score": score_data["score"],
                        "predicted_ctr": score_data["predicted_ctr_range"],
                        "grade": score_data["grade"],
                        "factors": score_data["factors"]
                    })

                # Sort by score (highest first)
                scored_titles.sort(key=lambda x: x["score"], reverse=True)

                return scored_titles
            else:
                # Fallback: generate simple titles
                return self._generate_fallback_titles(topic, count)

        except Exception as e:
            print(f"Error generating titles: {e}")
            return self._generate_fallback_titles(topic, count)

    def _generate_fallback_titles(self, topic: str, count: int) -> List[Dict]:
        """Generate fallback titles if AI generation fails"""
        templates = [
            f"How to {topic} in 2025",
            f"The Ultimate Guide to {topic}",
            f"{topic}: Everything You Need to Know",
            f"5 Ways to Improve Your {topic}",
            f"Why Your {topic} Isn't Working (And How to Fix It)"
        ]

        return [
            {
                "title": templates[i % len(templates)],
                "score": 50,
                "predicted_ctr": "4-6%",
                "grade": "C",
                "factors": []
            }
            for i in range(count)
        ]


# Singleton instance
_title_optimizer = None


def get_title_optimizer() -> TitleOptimizer:
    """Get or create title optimizer singleton"""
    global _title_optimizer
    if _title_optimizer is None:
        _title_optimizer = TitleOptimizer()
    return _title_optimizer
