from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float, Boolean, Enum, JSON
from datetime import datetime
from app.db.session import Base
from typing import Optional
import enum


class VideoProcessingStatus(str, enum.Enum):
    """Video processing pipeline status"""
    SYNCED = "synced"  # Synced from YouTube, not yet processed
    AUDIO_DOWNLOADING = "audio_downloading"  # Audio download in progress
    AUDIO_DOWNLOADED = "audio_downloaded"  # Audio downloaded successfully
    TRANSCRIBING = "transcribing"  # Transcription in progress
    TRANSCRIBED = "transcribed"  # Transcription complete
    INDEXING = "indexing"  # Vector indexing in progress
    COMPLETE = "complete"  # Fully processed and indexed
    ERROR = "error"  # Processing failed


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    google_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    channels: Mapped[list["Channel"]] = relationship(back_populates="owner")


class Channel(Base):
    __tablename__ = "channels"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    youtube_channel_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscribers: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    total_views: Mapped[int] = mapped_column(Integer, default=0) # Must be here
    total_watch_hours: Mapped[float] = mapped_column(Float, default=0.0) # Must be here
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    owner: Mapped[User | None] = relationship(back_populates="channels")
    videos: Mapped[list["Video"]] = relationship(back_populates="channel")


class Video(Base):
    __tablename__ = "videos"
    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    youtube_video_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(512))
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    ctr: Mapped[float] = mapped_column(Float, default=0.0)
    channel: Mapped[Channel] = relationship(back_populates="videos")
    transcript_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Processing status tracking
    processing_status: Mapped[str] = mapped_column(
        Enum(VideoProcessingStatus),
        default=VideoProcessingStatus.SYNCED,
        nullable=False
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # YouTube Analytics API metrics (NEW)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    average_view_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_view_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_minutes_watched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    card_click_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0)
    subscribers_lost: Mapped[int] = mapped_column(Integer, default=0)
    videos_added_to_playlists: Mapped[int] = mapped_column(Integer, default=0)
    first_24h_views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_analytics_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    analytics_available: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    retention_curve: Mapped[Optional["VideoRetentionCurve"]] = relationship(back_populates="video", uselist=False)
    traffic_sources: Mapped[list["VideoTrafficSource"]] = relationship(back_populates="video", cascade="all, delete-orphan")
    analytics_snapshots: Mapped[list["VideoAnalyticsDaily"]] = relationship(back_populates="video", cascade="all, delete-orphan")

    # Computed properties
    @property
    def engagement_rate(self) -> float:
        """(likes + comments + shares) / views * 100"""
        if self.views == 0:
            return 0.0
        return ((self.likes + self.comments + self.shares) / self.views) * 100

    @property
    def hook_strength(self) -> Optional[float]:
        """Retention at 30s - indicator of hook effectiveness"""
        if self.retention_curve:
            return self.retention_curve.retention_at_30s
        return None

    @property
    def subscriber_conversion_rate(self) -> float:
        """Subscribers gained per 1000 views"""
        if self.views == 0:
            return 0.0
        return (self.subscribers_gained / self.views) * 1000


class Idea(Base):
    __tablename__ = "ideas"
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    summary: Mapped[str] = mapped_column(Text)
    ideas_json: Mapped[str] = mapped_column(Text)
    outline: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Script(Base):
    __tablename__ = "scripts"
    id: Mapped[int] = mapped_column(primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"))
    content_md: Mapped[str] = mapped_column(Text)
    tone: Mapped[str | None] = mapped_column(String(64))
    minutes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# NEW ANALYTICS MODELS

class VideoAnalyticsDaily(Base):
    """Daily analytics snapshots for time-series analysis"""
    __tablename__ = "video_analytics_daily"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Core metrics (daily deltas)
    views_delta: Mapped[int] = mapped_column(Integer, default=0)
    estimated_minutes_watched_delta: Mapped[int] = mapped_column(Integer, default=0)
    average_view_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_view_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Engagement deltas
    likes_delta: Mapped[int] = mapped_column(Integer, default=0)
    comments_delta: Mapped[int] = mapped_column(Integer, default=0)
    shares_delta: Mapped[int] = mapped_column(Integer, default=0)
    subscribers_gained_delta: Mapped[int] = mapped_column(Integer, default=0)

    # Traffic source breakdown (JSON)
    traffic_sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    playback_locations: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    video: Mapped["Video"] = relationship(back_populates="analytics_snapshots")


class VideoRetentionCurve(Base):
    """Audience retention curves for hook and engagement analysis"""
    __tablename__ = "video_retention_curves"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Retention data points (JSON array)
    # Format: [{"elapsed_seconds": 0, "retention_percentage": 100}, ...]
    retention_points: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Key retention milestones (denormalized for quick access)
    retention_at_10s: Mapped[float | None] = mapped_column(Float, nullable=True)
    retention_at_30s: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)  # Hook strength
    retention_at_60s: Mapped[float | None] = mapped_column(Float, nullable=True)
    retention_at_halfway: Mapped[float | None] = mapped_column(Float, nullable=True)
    retention_at_end: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Aggregate metrics
    median_retention_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    critical_drop_point_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    video: Mapped["Video"] = relationship(back_populates="retention_curve")


class VideoTrafficSource(Base):
    """Traffic source breakdown per video"""
    __tablename__ = "video_traffic_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # YT_SEARCH, YT_SUGGESTED, etc.
    source_detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # Specific search term, referring URL

    views: Mapped[int] = mapped_column(Integer, default=0)
    watch_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    percentage_of_views: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    video: Mapped["Video"] = relationship(back_populates="traffic_sources")


class ChannelDemographics(Base):
    """Audience demographics for channel-level insights"""
    __tablename__ = "channel_demographics"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)

    dimension_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'age_group', 'gender', 'geography'
    dimension_value: Mapped[str] = mapped_column(String(100), nullable=False)  # 'age25-34', 'male', 'US'

    views_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    watch_time_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class AIInsight(Base):
    """Cached AI-generated insights for channels"""
    __tablename__ = "ai_insights"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'performance_drivers', 'content_recommendations', etc.

    # Insight data (structured JSON)
    insight_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Metadata
    videos_analyzed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1

    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Cache TTL


