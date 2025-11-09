#!/usr/bin/env python3
"""
Quick diagnostic script to check which videos are in the database.
This helps debug the "Video X not found in database" issue.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.models import Video, Channel, VideoProcessingStatus

def main():
    db = SessionLocal()
    
    print("\n" + "="*60)
    print("📊 Videos in Database")
    print("="*60 + "\n")
    
    # Get all channels
    channels = db.query(Channel).all()
    
    if not channels:
        print("⚠️  No channels found in database!")
        print("   → Please sync a channel first from the UI\n")
        db.close()
        return
    
    for channel in channels:
        print(f"📺 Channel: {channel.name} (ID: {channel.id})")
        print(f"   YouTube ID: {channel.youtube_channel_id}")
        print(f"   Subscriber Count: {channel.subscriber_count:,}" if channel.subscriber_count else "")
        
        # Get videos for this channel
        videos = db.query(Video).filter(Video.channel_id == channel.id).all()
        
        if not videos:
            print(f"   ⚠️  No videos found for this channel\n")
            continue
        
        print(f"   Total Videos: {len(videos)}\n")
        
        # Show status breakdown
        status_counts = {}
        for video in videos:
            status = video.processing_status.value if video.processing_status else 'unknown'
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("   Processing Status Breakdown:")
        for status, count in sorted(status_counts.items()):
            emoji = {
                'synced': '📥',
                'queued': '⏳',
                'transcribing': '🎙️',
                'transcribed': '✍️',
                'indexing': '📑',
                'complete': '✅',
                'error': '❌'
            }.get(status, '❓')
            print(f"   {emoji} {status.upper()}: {count} videos")
        
        print("\n   Recent videos:")
        recent_videos = sorted(videos, key=lambda v: v.id, reverse=True)[:10]
        for video in recent_videos:
            status = video.processing_status.value if video.processing_status else 'unknown'
            status_emoji = {
                'synced': '📥',
                'queued': '⏳',
                'transcribing': '🎙️',
                'transcribed': '✍️',
                'indexing': '📑',
                'complete': '✅',
                'error': '❌'
            }.get(status, '❓')
            
            title = video.title[:50] + '...' if len(video.title) > 50 else video.title
            print(f"   {status_emoji} ID {video.id}: {title}")
            print(f"      YouTube: {video.youtube_video_id} | Status: {status}")
            if video.processing_error:
                error = video.processing_error[:60] + '...' if len(video.processing_error) > 60 else video.processing_error
                print(f"      Error: {error}")
        
        print("\n" + "-"*60 + "\n")
    
    db.close()
    
    print("💡 Tips:")
    print("   • Videos with 'error' status can be re-queued by re-syncing")
    print("   • Videos showing 'not found in database' in logs are from old tasks")
    print("   • Clear the Celery queue and re-sync to fix 'not found' issues")
    print("\n")

if __name__ == "__main__":
    main()

