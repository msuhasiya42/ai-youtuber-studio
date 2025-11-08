"""add_youtube_analytics_tables_and_fields

Revision ID: b3f8c21a92d4
Revises: a207e77698e5
Create Date: 2025-01-08 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b3f8c21a92d4'
down_revision: Union[str, None] = 'a207e77698e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new analytics fields to videos table
    op.add_column('videos', sa.Column('comments', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('videos', sa.Column('shares', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('videos', sa.Column('average_view_duration_seconds', sa.Integer(), nullable=True))
    op.add_column('videos', sa.Column('average_view_percentage', sa.Float(), nullable=True))
    op.add_column('videos', sa.Column('estimated_minutes_watched', sa.Integer(), nullable=True))
    op.add_column('videos', sa.Column('card_click_rate', sa.Float(), nullable=True))
    op.add_column('videos', sa.Column('subscribers_gained', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('videos', sa.Column('subscribers_lost', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('videos', sa.Column('videos_added_to_playlists', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('videos', sa.Column('first_24h_views', sa.Integer(), nullable=True))
    op.add_column('videos', sa.Column('last_analytics_sync_at', sa.DateTime(), nullable=True))
    op.add_column('videos', sa.Column('analytics_available', sa.Boolean(), nullable=False, server_default='false'))

    # Create indexes for analytics fields
    op.create_index('idx_videos_retention', 'videos', ['average_view_percentage'], unique=False, postgresql_where=sa.text('average_view_percentage IS NOT NULL'))
    op.create_index('idx_videos_engagement', 'videos', ['channel_id', 'views'], unique=False, postgresql_where=sa.text('views > 0'))
    op.create_index('idx_videos_sync_status', 'videos', ['last_analytics_sync_at', 'analytics_available'], unique=False)

    # Create video_analytics_daily table
    op.create_table('video_analytics_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.Column('views_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_minutes_watched_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_view_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('average_view_percentage', sa.Float(), nullable=True),
        sa.Column('likes_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comments_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shares_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('subscribers_gained_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('traffic_sources', sa.JSON(), nullable=True),
        sa.Column('playback_locations', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_id', 'snapshot_date', name='uq_video_analytics_daily_video_date')
    )
    op.create_index('idx_analytics_daily_video', 'video_analytics_daily', ['video_id', 'snapshot_date'], unique=False)
    op.create_index('idx_analytics_daily_date', 'video_analytics_daily', ['snapshot_date'], unique=False)

    # Create video_retention_curves table
    op.create_table('video_retention_curves',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('retention_points', sa.JSON(), nullable=False),
        sa.Column('retention_at_10s', sa.Float(), nullable=True),
        sa.Column('retention_at_30s', sa.Float(), nullable=True),
        sa.Column('retention_at_60s', sa.Float(), nullable=True),
        sa.Column('retention_at_halfway', sa.Float(), nullable=True),
        sa.Column('retention_at_end', sa.Float(), nullable=True),
        sa.Column('median_retention_percentage', sa.Float(), nullable=True),
        sa.Column('critical_drop_point_seconds', sa.Integer(), nullable=True),
        sa.Column('synced_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_id', name='uq_video_retention_curves_video')
    )
    op.create_index('idx_retention_hook', 'video_retention_curves', ['retention_at_30s'], unique=False)
    op.create_index('idx_retention_median', 'video_retention_curves', ['median_retention_percentage'], unique=False)

    # Create video_traffic_sources table
    op.create_table('video_traffic_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_detail', sa.Text(), nullable=True),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('watch_time_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('percentage_of_views', sa.Float(), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_id', 'source_type', 'source_detail', name='uq_video_traffic_sources_video_source')
    )
    op.create_index('idx_traffic_source_type', 'video_traffic_sources', ['video_id', 'source_type'], unique=False)
    op.create_index('idx_traffic_source_performance', 'video_traffic_sources', ['views', 'watch_time_minutes'], unique=False)

    # Create channel_demographics table
    op.create_table('channel_demographics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('dimension_type', sa.String(length=50), nullable=False),
        sa.Column('dimension_value', sa.String(length=100), nullable=False),
        sa.Column('views_percentage', sa.Float(), nullable=True),
        sa.Column('watch_time_percentage', sa.Float(), nullable=True),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel_id', 'dimension_type', 'dimension_value', 'snapshot_date', name='uq_channel_demographics_channel_dim_date')
    )
    op.create_index('idx_demographics_channel', 'channel_demographics', ['channel_id', 'snapshot_date'], unique=False)
    op.create_index('idx_demographics_type', 'channel_demographics', ['dimension_type', 'dimension_value'], unique=False)

    # Create ai_insights table
    op.create_table('ai_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('insight_type', sa.String(length=50), nullable=False),
        sa.Column('insight_data', sa.JSON(), nullable=False),
        sa.Column('videos_analyzed', sa.Integer(), nullable=True),
        sa.Column('analysis_period_days', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel_id', 'insight_type', name='uq_ai_insights_channel_type')
    )
    op.create_index('idx_insights_channel_type', 'ai_insights', ['channel_id', 'insight_type'], unique=False)
    op.create_index('idx_insights_expiry', 'ai_insights', ['expires_at'], unique=False, postgresql_where=sa.text('expires_at IS NOT NULL'))


def downgrade() -> None:
    # Drop ai_insights table
    op.drop_index('idx_insights_expiry', table_name='ai_insights')
    op.drop_index('idx_insights_channel_type', table_name='ai_insights')
    op.drop_table('ai_insights')

    # Drop channel_demographics table
    op.drop_index('idx_demographics_type', table_name='channel_demographics')
    op.drop_index('idx_demographics_channel', table_name='channel_demographics')
    op.drop_table('channel_demographics')

    # Drop video_traffic_sources table
    op.drop_index('idx_traffic_source_performance', table_name='video_traffic_sources')
    op.drop_index('idx_traffic_source_type', table_name='video_traffic_sources')
    op.drop_table('video_traffic_sources')

    # Drop video_retention_curves table
    op.drop_index('idx_retention_median', table_name='video_retention_curves')
    op.drop_index('idx_retention_hook', table_name='video_retention_curves')
    op.drop_table('video_retention_curves')

    # Drop video_analytics_daily table
    op.drop_index('idx_analytics_daily_date', table_name='video_analytics_daily')
    op.drop_index('idx_analytics_daily_video', table_name='video_analytics_daily')
    op.drop_table('video_analytics_daily')

    # Drop indexes from videos table
    op.drop_index('idx_videos_sync_status', table_name='videos')
    op.drop_index('idx_videos_engagement', table_name='videos')
    op.drop_index('idx_videos_retention', table_name='videos')

    # Drop columns from videos table
    op.drop_column('videos', 'analytics_available')
    op.drop_column('videos', 'last_analytics_sync_at')
    op.drop_column('videos', 'first_24h_views')
    op.drop_column('videos', 'videos_added_to_playlists')
    op.drop_column('videos', 'subscribers_lost')
    op.drop_column('videos', 'subscribers_gained')
    op.drop_column('videos', 'card_click_rate')
    op.drop_column('videos', 'estimated_minutes_watched')
    op.drop_column('videos', 'average_view_percentage')
    op.drop_column('videos', 'average_view_duration_seconds')
    op.drop_column('videos', 'shares')
    op.drop_column('videos', 'comments')
