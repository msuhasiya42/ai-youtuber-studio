from typing import Dict, List


class InsightsPromptTemplates:
    """LLM prompt templates for generating narrative insights from YouTube Analytics data."""

    @staticmethod
    def performance_drivers_prompt(video_data: List[Dict], top_n: int = 5) -> str:
        """
        Generate prompt to identify what makes top videos successful.

        Args:
            video_data: List of video dicts with metrics
            top_n: Number of top videos to analyze

        Returns:
            LLM prompt string
        """
        video_summaries = "\n".join([
            f"#{i+1}. '{v['title']}'\n"
            f"   - Views: {v['views']:,} | Retention: {v.get('retention', 0):.1f}% | "
            f"Hook (30s): {v.get('hook_strength', 0):.1f}% | Engagement: {v.get('engagement_rate', 0):.2f}%\n"
            f"   - Duration: {v.get('duration_minutes', 0):.1f} min | "
            f"Top Traffic: {v.get('top_traffic_source', 'N/A')} ({v.get('traffic_percentage', 0):.1f}%)\n"
            f"   - Subs gained: {v.get('subscribers_gained', 0)} | "
            f"First 24h: {v.get('first_24h_views', 'N/A')} views"
            for i, v in enumerate(video_data[:top_n])
        ])

        return f"""You are a YouTube analytics expert. Analyze these top-performing videos and identify WHY they succeeded.

TOP {top_n} VIDEOS BY PERFORMANCE:
{video_summaries}

Provide a structured analysis in JSON format:

{{
  "common_success_patterns": [
    "List 3-5 patterns that these videos share (content themes, formats, hooks, etc.)"
  ],
  "key_performance_drivers": [
    {{
      "driver": "Name of driver (e.g., Hook Strength, Duration, Traffic Source)",
      "impact": "high/medium/low",
      "explanation": "Why this drives performance"
    }}
  ],
  "content_themes": [
    "List 3-5 content themes/topics that resonate most"
  ],
  "structural_patterns": [
    "Video structure patterns (length, pacing, hook style, etc.)"
  ],
  "actionable_recommendations": [
    "5 specific, actionable recommendations based on these patterns"
  ],
  "success_formula": "One-sentence summary of what makes videos successful on this channel"
}}

Be specific, data-driven, and focus on reproducible patterns. Output valid JSON only."""

    @staticmethod
    def content_idea_generation_prompt(
        channel_context: str,
        top_topics: List[str],
        audience_demographics: Dict,
        performance_patterns: Dict
    ) -> str:
        """Generate prompt for content idea suggestions."""

        topics_str = ", ".join(top_topics) if top_topics else "Not available"

        demo_summary = []
        if audience_demographics.get('top_age_group'):
            demo_summary.append(f"Age: {audience_demographics['top_age_group']}")
        if audience_demographics.get('top_gender'):
            demo_summary.append(f"Gender: {audience_demographics['top_gender']}")
        if audience_demographics.get('top_country'):
            demo_summary.append(f"Location: {audience_demographics['top_country']}")

        demo_str = ", ".join(demo_summary) if demo_summary else "Not available"

        sweet_spot = performance_patterns.get('optimal_duration', 'N/A')
        avg_retention = performance_patterns.get('avg_retention', 'N/A')

        return f"""You are a YouTube content strategist. Based on this channel's performance data, suggest 10 video ideas that are likely to succeed.

CHANNEL CONTEXT:
{channel_context}

TOP PERFORMING TOPICS:
{topics_str}

AUDIENCE DEMOGRAPHICS:
{demo_str}

PERFORMANCE PATTERNS:
- Optimal video length: {sweet_spot}
- Average retention: {avg_retention}

Generate 10 video ideas that:
1. Align with proven successful topics
2. Appeal to the core demographic
3. Have high search/discovery potential
4. Are specific and actionable

For each idea, provide (in JSON format):

{{
  "video_ideas": [
    {{
      "title": "Optimized title for CTR (50-60 characters)",
      "hook_concept": "What happens in the first 30 seconds",
      "content_outline": "Brief 3-4 point outline",
      "why_it_will_perform": "Data-driven reasoning",
      "estimated_length": "Target duration",
      "target_keywords": ["keyword1", "keyword2", "keyword3"],
      "expected_traffic_source": "Search/Suggested/etc",
      "thumbnail_concept": "Brief thumbnail description"
    }}
  ]
}}

Output valid JSON only."""

    @staticmethod
    def retention_analysis_prompt(
        video_title: str,
        video_stats: Dict,
        retention_milestones: Dict,
        significant_drops: List[Dict]
    ) -> str:
        """Correlate retention drops with content moments."""

        stats_str = f"""
- Total views: {video_stats.get('views', 0):,}
- Overall retention: {video_stats.get('average_retention', 0):.1f}%
- Duration: {video_stats.get('duration_minutes', 0):.1f} minutes
- Engagement rate: {video_stats.get('engagement_rate', 0):.2f}%"""

        milestones_str = f"""
- 10s: {retention_milestones.get('10s', 0):.1f}%
- 30s (Hook): {retention_milestones.get('30s', 0):.1f}%
- 60s: {retention_milestones.get('60s', 0):.1f}%
- Halfway: {retention_milestones.get('halfway', 0):.1f}%
- End: {retention_milestones.get('end', 0):.1f}%"""

        drops_str = "\n".join([
            f"- {drop['timestamp']:.0f}s: {drop['drop_percentage']:.1f}% drop"
            for drop in significant_drops
        ]) if significant_drops else "  No significant drops detected"

        return f"""Analyze the audience retention pattern for this video and provide actionable insights.

VIDEO: "{video_title}"

VIDEO STATS:
{stats_str}

RETENTION MILESTONES:
{milestones_str}

SIGNIFICANT DROP POINTS:
{drops_str}

Provide analysis in JSON format:

{{
  "hook_analysis": {{
    "strength": "weak/moderate/strong",
    "rating_out_of_10": 0,
    "feedback": "Specific feedback on the hook (first 30s)"
  }},
  "retention_pattern_analysis": {{
    "overall_assessment": "Description of the retention curve",
    "strengths": ["What worked well"],
    "weaknesses": ["What caused drop-offs"]
  }},
  "drop_point_analysis": [
    {{
      "timestamp": "Timestamp where drop occurred",
      "likely_cause": "Educated guess on why viewers left",
      "fix_suggestion": "How to improve this section"
    }}
  ],
  "positive_moments": [
    {{
      "timestamp": "Where retention increased or held steady",
      "why_it_worked": "What kept viewers engaged"
    }}
  ],
  "recommendations": [
    "5 specific recommendations to improve retention"
  ],
  "optimal_length_suggestion": "Based on the curve, suggested video length",
  "pacing_feedback": "Comments on video pacing and structure"
}}

Output valid JSON only."""

    @staticmethod
    def traffic_source_insights_prompt(
        video_title: str,
        traffic_breakdown: List[Dict],
        video_metadata: Dict
    ) -> str:
        """Generate insights about traffic source performance."""

        traffic_str = "\n".join([
            f"- {source['source_type']}: {source['percentage']:.1f}% ({source['views']:,} views) | "
            f"Avg watch time: {source.get('avg_watch_time', 0):.1f} min"
            for source in traffic_breakdown
        ])

        metadata_str = f"""
- Published: {video_metadata.get('published_date', 'N/A')}
- Total views: {video_metadata.get('total_views', 0):,}
- Retention: {video_metadata.get('retention', 0):.1f}%
- Engagement: {video_metadata.get('engagement_rate', 0):.2f}%"""

        return f"""Analyze traffic source performance for this video and provide optimization recommendations.

VIDEO: "{video_title}"

VIDEO METADATA:
{metadata_str}

TRAFFIC SOURCES:
{traffic_str}

Provide analysis in JSON format:

{{
  "traffic_distribution_assessment": {{
    "health": "healthy/unbalanced/concerning",
    "explanation": "Why the distribution is good or bad"
  }},
  "source_performance_analysis": [
    {{
      "source": "Source name",
      "performance": "excellent/good/average/poor",
      "reasoning": "Why this source performs this way"
    }}
  ],
  "underperforming_sources": [
    {{
      "source": "Source name",
      "issue": "What's wrong",
      "opportunity": "How much potential exists",
      "fix": "How to improve"
    }}
  ],
  "optimization_priorities": [
    {{
      "priority": "1/2/3",
      "action": "Specific action to take",
      "expected_impact": "What improvement to expect",
      "difficulty": "easy/medium/hard"
    }}
  ],
  "content_market_fit_assessment": "What the traffic mix tells us about content-market fit",
  "next_steps": [
    "3-5 concrete next steps prioritized by impact"
  ]
}}

Output valid JSON only."""

    @staticmethod
    def comprehensive_channel_insights_prompt(
        channel_stats: Dict,
        top_performers: List[Dict],
        patterns: Dict,
        demographics: Dict
    ) -> str:
        """Generate comprehensive channel-level insights."""

        stats_str = f"""
- Total videos analyzed: {channel_stats.get('total_videos', 0)}
- Avg views per video: {channel_stats.get('avg_views', 0):,}
- Avg retention: {channel_stats.get('avg_retention', 0):.1f}%
- Avg engagement rate: {channel_stats.get('avg_engagement', 0):.2f}%
- Total subscribers gained (from videos): {channel_stats.get('total_subscribers_gained', 0):,}"""

        top_videos_str = "\n".join([
            f"{i+1}. '{v['title']}' - {v.get('views', 0):,} views, {v.get('retention', 0):.1f}% retention"
            for i, v in enumerate(top_performers[:5])
        ])

        patterns_str = f"""
- Optimal duration: {patterns.get('optimal_duration', 'N/A')}
- Best hook retention: {patterns.get('best_hook', 0):.1f}%
- Best posting day: {patterns.get('best_day', 'N/A')}
- Dominant traffic source: {patterns.get('dominant_traffic', 'N/A')}"""

        demo_str = f"""
- Primary age group: {demographics.get('top_age', 'N/A')} ({demographics.get('age_percentage', 0):.1f}%)
- Primary gender: {demographics.get('top_gender', 'N/A')} ({demographics.get('gender_percentage', 0):.1f}%)
- Top location: {demographics.get('top_country', 'N/A')} ({demographics.get('country_percentage', 0):.1f}%)"""

        return f"""You are a YouTube growth strategist. Provide a comprehensive analysis and growth strategy for this channel.

CHANNEL STATS:
{stats_str}

TOP 5 PERFORMING VIDEOS:
{top_videos_str}

PERFORMANCE PATTERNS:
{patterns_str}

AUDIENCE DEMOGRAPHICS:
{demo_str}

Provide a comprehensive analysis in JSON format:

{{
  "channel_health_score": {{
    "overall_score": 0-100,
    "rating": "excellent/good/average/needs_improvement",
    "explanation": "Overall assessment"
  }},
  "strengths": [
    {{
      "strength": "What the channel does well",
      "evidence": "Data supporting this",
      "leverage_opportunity": "How to double down on this"
    }}
  ],
  "weaknesses": [
    {{
      "weakness": "What needs improvement",
      "impact": "high/medium/low",
      "fix": "How to address it"
    }}
  ],
  "growth_opportunities": [
    {{
      "opportunity": "Growth opportunity",
      "potential_impact": "Estimated impact",
      "effort_required": "low/medium/high",
      "priority": 1-5,
      "action_plan": "Specific steps to capture this opportunity"
    }}
  ],
  "audience_insights": {{
    "who_watches": "Detailed description of core audience",
    "what_resonates": "What content this audience loves",
    "untapped_segments": "Potential audience segments to target"
  }},
  "content_strategy": {{
    "what_to_create_more": ["Content types to double down on"],
    "what_to_avoid": ["Content types that underperform"],
    "new_directions": ["New content angles to explore"],
    "collaboration_opportunities": ["Types of creators to collaborate with"]
  }},
  "90_day_action_plan": [
    {{
      "month": 1-3,
      "focus": "What to focus on",
      "specific_actions": ["Actionable steps"],
      "expected_results": "What to expect"
    }}
  ],
  "success_metrics_to_track": [
    "KPIs to monitor for growth"
  ]
}}

Be specific, actionable, and data-driven. Output valid JSON only."""

    @staticmethod
    def viral_potential_analysis_prompt(
        video_data: Dict,
        channel_benchmarks: Dict
    ) -> str:
        """Analyze why a video went viral or has viral potential."""

        video_str = f"""
- Title: {video_data.get('title', 'N/A')}
- Views: {video_data.get('views', 0):,}
- Views vs channel avg: {video_data.get('views_vs_avg', '0')}x
- Retention: {video_data.get('retention', 0):.1f}%
- Hook retention: {video_data.get('hook_retention', 0):.1f}%
- Engagement rate: {video_data.get('engagement_rate', 0):.2f}%
- Watch time: {video_data.get('watch_time', 0):,} minutes
- Suggested video traffic: {video_data.get('suggested_percentage', 0):.1f}%
- First 24h views: {video_data.get('first_24h_views', 0):,}"""

        benchmarks_str = f"""
- Channel avg views: {channel_benchmarks.get('avg_views', 0):,}
- Channel avg retention: {channel_benchmarks.get('avg_retention', 0):.1f}%
- Channel avg engagement: {channel_benchmarks.get('avg_engagement', 0):.2f}%"""

        return f"""Analyze why this video performed exceptionally well and how to replicate its success.

VIDEO PERFORMANCE:
{video_str}

CHANNEL BENCHMARKS:
{benchmarks_str}

Provide analysis in JSON format:

{{
  "virality_factors": [
    {{
      "factor": "What contributed to viral performance",
      "importance": "critical/high/medium",
      "evidence": "Data supporting this factor",
      "replicability": "easy/medium/hard to replicate"
    }}
  ],
  "algorithm_signals": [
    "Specific algorithm signals this video triggered (high CTR, watch time, etc.)"
  ],
  "audience_response_analysis": {{
    "what_hooked_them": "Why viewers clicked and stayed",
    "what_made_them_engage": "Why they liked/commented/shared",
    "emotional_triggers": ["Emotions this video evoked"]
  }},
  "replication_blueprint": {{
    "replicable_elements": ["Specific elements that can be reused"],
    "unique_elements": ["One-off elements that can't be replicated"],
    "content_formula": "Template for similar videos"
  }},
  "next_video_suggestions": [
    {{
      "idea": "Video idea that could replicate this success",
      "why_it_could_work": "Reasoning",
      "confidence": "high/medium/low"
    }}
  ],
  "warnings": [
    "Things to avoid when trying to replicate (chasing trends too hard, etc.)"
  ]
}}

Output valid JSON only."""
