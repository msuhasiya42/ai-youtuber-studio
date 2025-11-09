#!/usr/bin/env python3
"""
Test script to verify Analytics API implementation.

Usage:
    cd /Users/mayursuhasiya/Desktop/Projects/ai-youtuber-studio/backend
    docker compose exec backend python scripts/test_analytics_api.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.models import (
    Video, 
    Channel, 
    VideoAnalyticsDaily, 
    VideoRetentionCurve, 
    VideoTrafficSource,
    ChannelDemographics,
    AIInsight
)
from sqlalchemy import inspect


def test_database_tables():
    """Test that all analytics tables exist in the database."""
    print("=" * 80)
    print("Testing Database Tables")
    print("=" * 80)
    
    db = SessionLocal()
    inspector = inspect(db.bind)
    table_names = inspector.get_table_names()
    
    required_tables = [
        'videos',
        'channels',
        'video_analytics_daily',
        'video_retention_curves',
        'video_traffic_sources',
        'channel_demographics',
        'ai_insights'
    ]
    
    missing_tables = []
    for table in required_tables:
        if table in table_names:
            print(f"✅ Table '{table}' exists")
        else:
            print(f"❌ Table '{table}' NOT FOUND")
            missing_tables.append(table)
    
    if missing_tables:
        print(f"\n⚠️  Missing tables: {missing_tables}")
        print("Run: docker compose exec backend alembic upgrade head")
        return False
    else:
        print("\n✅ All analytics tables exist!")
        return True


def test_video_model_fields():
    """Test that Video model has all new analytics fields."""
    print("\n" + "=" * 80)
    print("Testing Video Model Fields")
    print("=" * 80)
    
    db = SessionLocal()
    inspector = inspect(db.bind)
    columns = [col['name'] for col in inspector.get_columns('videos')]
    
    required_fields = [
        'comments',
        'shares',
        'average_view_duration_seconds',
        'average_view_percentage',
        'estimated_minutes_watched',
        'card_click_rate',
        'subscribers_gained',
        'subscribers_lost',
        'videos_added_to_playlists',
        'first_24h_views',
        'last_analytics_sync_at',
        'analytics_available'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field in columns:
            print(f"✅ Field '{field}' exists in videos table")
        else:
            print(f"❌ Field '{field}' NOT FOUND in videos table")
            missing_fields.append(field)
    
    if missing_fields:
        print(f"\n⚠️  Missing fields: {missing_fields}")
        print("Run: docker compose exec backend alembic upgrade head")
        return False
    else:
        print("\n✅ All analytics fields exist in Video model!")
        return True


def test_data_availability():
    """Test if there's any analytics data in the database."""
    print("\n" + "=" * 80)
    print("Testing Data Availability")
    print("=" * 80)
    
    db = SessionLocal()
    
    # Count records
    video_count = db.query(Video).count()
    channel_count = db.query(Channel).count()
    analytics_count = db.query(VideoAnalyticsDaily).count()
    retention_count = db.query(VideoRetentionCurve).count()
    traffic_count = db.query(VideoTrafficSource).count()
    insights_count = db.query(AIInsight).count()
    
    print(f"📊 Videos: {video_count}")
    print(f"📺 Channels: {channel_count}")
    print(f"📈 Analytics Daily Records: {analytics_count}")
    print(f"📉 Retention Curves: {retention_count}")
    print(f"🚦 Traffic Sources: {traffic_count}")
    print(f"🤖 AI Insights: {insights_count}")
    
    # Check for videos with analytics
    videos_with_analytics = db.query(Video).filter(Video.analytics_available == True).count()
    print(f"\n✅ Videos with analytics synced: {videos_with_analytics}")
    
    if video_count > 0 and videos_with_analytics == 0:
        print("\n⚠️  Videos exist but no analytics synced yet.")
        print("Run analytics sync via: POST /api/analytics/sync/{channel_id}")
    
    return True


def test_computed_properties():
    """Test Video model computed properties."""
    print("\n" + "=" * 80)
    print("Testing Computed Properties")
    print("=" * 80)
    
    db = SessionLocal()
    
    # Get a video to test computed properties
    video = db.query(Video).first()
    
    if not video:
        print("⚠️  No videos in database. Cannot test computed properties.")
        return False
    
    print(f"\nTesting with video: {video.title[:50]}...")
    
    try:
        engagement_rate = video.engagement_rate
        print(f"✅ engagement_rate: {engagement_rate:.2f}%")
    except Exception as e:
        print(f"❌ engagement_rate failed: {e}")
        return False
    
    try:
        conversion_rate = video.subscriber_conversion_rate
        print(f"✅ subscriber_conversion_rate: {conversion_rate:.4f}%")
    except Exception as e:
        print(f"❌ subscriber_conversion_rate failed: {e}")
        return False
    
    try:
        hook_strength = video.hook_strength
        if hook_strength is not None:
            print(f"✅ hook_strength: {hook_strength:.2f}%")
        else:
            print(f"✅ hook_strength: None (retention curve not synced)")
    except Exception as e:
        print(f"❌ hook_strength failed: {e}")
        return False
    
    print("\n✅ All computed properties work correctly!")
    return True


def test_api_imports():
    """Test that all analytics modules can be imported."""
    print("\n" + "=" * 80)
    print("Testing Python Module Imports")
    print("=" * 80)
    
    try:
        from app.services.youtube_analytics_client import YouTubeAnalyticsClient
        print("✅ YouTubeAnalyticsClient imported")
    except Exception as e:
        print(f"❌ Failed to import YouTubeAnalyticsClient: {e}")
        return False
    
    try:
        from app.services.analytics_sync_worker import (
            sync_video_analytics,
            sync_channel_analytics_batch,
            sync_channel_demographics,
            daily_analytics_refresh
        )
        print("✅ Analytics sync tasks imported")
    except Exception as e:
        print(f"❌ Failed to import analytics sync tasks: {e}")
        return False
    
    try:
        from app.services.advanced_pattern_analyzer import AdvancedPatternAnalyzer
        print("✅ AdvancedPatternAnalyzer imported")
    except Exception as e:
        print(f"❌ Failed to import AdvancedPatternAnalyzer: {e}")
        return False
    
    try:
        from app.services.insights_generation_prompts import (
            performance_drivers_prompt,
            content_idea_generation_prompt,
            retention_analysis_prompt
        )
        print("✅ Insights generation prompts imported")
    except Exception as e:
        print(f"❌ Failed to import insights prompts: {e}")
        return False
    
    try:
        from app.api import analytics
        print("✅ Analytics API router imported")
    except Exception as e:
        print(f"❌ Failed to import analytics router: {e}")
        return False
    
    print("\n✅ All modules import successfully!")
    return True


def main():
    """Run all tests."""
    print("\n")
    print("🚀" * 40)
    print("Analytics Engine - Implementation Test Suite")
    print("🚀" * 40)
    print("\n")
    
    results = []
    
    # Run all tests
    results.append(("Database Tables", test_database_tables()))
    results.append(("Video Model Fields", test_video_model_fields()))
    results.append(("Data Availability", test_data_availability()))
    results.append(("Computed Properties", test_computed_properties()))
    results.append(("API Imports", test_api_imports()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 All tests passed! Analytics Engine is ready to use.")
        print("\nNext steps:")
        print("1. Start frontend: cd frontend && npm run dev")
        print("2. Navigate to: http://localhost:5173/analytics")
        print("3. Click 'Sync Analytics' to pull data from YouTube")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

