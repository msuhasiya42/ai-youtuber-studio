from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float, Boolean, Enum
from datetime import datetime
from app.db.session import Base
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


