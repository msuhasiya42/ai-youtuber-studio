const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

// ========== Type Definitions ==========

export interface VideoAnalytics {
  video_id: number;
  youtube_video_id: string;
  title: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  average_view_duration_seconds: number | null;
  average_view_percentage: number | null;
  estimated_minutes_watched: number | null;
  subscribers_gained: number;
  subscribers_lost: number;
  first_24h_views: number | null;
  engagement_rate: number;
  subscriber_conversion_rate: number;
  hook_strength: number | null;
  analytics_available: boolean;
  last_analytics_sync_at: string | null;
}

export interface RetentionPoint {
  elapsed_seconds: number;
  retention_percentage: number;
}

export interface RetentionCurve {
  video_id: number;
  youtube_video_id: string;
  title: string;
  retention_points: RetentionPoint[];
  retention_at_10s: number | null;
  retention_at_30s: number | null;
  retention_at_60s: number | null;
  retention_at_halfway: number | null;
  retention_at_end: number | null;
  median_retention_percentage: number | null;
  critical_drop_point_seconds: number | null;
}

export interface TrafficSource {
  source_type: string;
  source_detail: string | null;
  views: number;
  watch_time_minutes: number;
  percentage_of_views: number;
}

export interface TrafficSourcesResponse {
  video_id: number;
  youtube_video_id: string;
  title: string;
  traffic_sources: TrafficSource[];
}

export interface ChannelSummary {
  channel_id: number;
  channel_name: string;
  total_videos_analyzed: number;
  total_videos: number;
  summary: {
    total_views: number;
    total_watch_time_minutes: number;
    total_watch_time_hours: number;
    avg_views_per_video: number;
    avg_retention_percentage: number;
    avg_engagement_rate: number;
    avg_hook_strength: number | null;
    total_subscribers_gained: number;
  };
  top_performers: Array<{
    video_id: number;
    youtube_video_id: string;
    title: string;
    views: number;
    retention: number | null;
    engagement_rate: number;
    hook_strength: number | null;
  }>;
}

export interface DurationAnalysis {
  channel_id: number;
  videos_analyzed: number;
  duration_buckets: Array<{
    range: string;
    avg_retention: number;
    video_count: number;
  }>;
  optimal_duration_range: string;
  correlation_coefficient: number;
}

export interface HookAnalysis {
  channel_id: number;
  videos_analyzed: number;
  avg_hook_strength: number;
  hook_performance_buckets: Array<{
    range: string;
    avg_views: number;
    video_count: number;
  }>;
  strong_hooks_count: number;
  weak_hooks_count: number;
  recommendations: string[];
}

export interface TrafficSourceAnalysis {
  channel_id: number;
  traffic_sources: Array<{
    source_type: string;
    total_views: number;
    avg_retention: number;
    avg_engagement: number;
    percentage_of_total: number;
  }>;
  best_performing_source: string;
  recommendations: string[];
}

export interface PostingTimeAnalysis {
  channel_id: number;
  day_of_week_performance: Array<{
    day: string;
    avg_views: number;
    video_count: number;
  }>;
  best_day: string;
  hour_of_day_performance: Array<{
    hour: number;
    avg_views: number;
    video_count: number;
  }>;
  recommendations: string[];
}

export interface EngagementAnalysis {
  channel_id: number;
  avg_engagement_rate: number;
  like_rate: number;
  comment_rate: number;
  share_rate: number;
  high_engagement_videos_count: number;
  engagement_drivers: string[];
  recommendations: string[];
}

export interface ContentRecommendations {
  channel_id: number;
  recommendations: Array<{
    category: string;
    suggestions: string[];
    priority: string;
  }>;
  top_opportunities: string[];
}

export interface ComprehensiveInsights {
  channel_id: number;
  cached: boolean;
  generated_at: string;
  expires_at: string;
  performance_overview: any;
  pattern_analysis: any;
  content_recommendations: any;
  actionable_insights: string[];
}

export interface PerformanceDrivers {
  channel_id: number;
  channel_name: string;
  videos_analyzed: number;
  use_llm: boolean;
  key_success_factors?: string[];
  common_patterns?: string[];
  optimization_opportunities?: string[];
  recommendations?: string[];
  raw_video_data?: any[];
}

export interface RetentionAnalysis {
  video_id: number;
  youtube_video_id: string;
  title: string;
  use_llm: boolean;
  retention_insights?: {
    overall_performance: string;
    critical_moments: string[];
    improvement_suggestions: string[];
  };
  raw_data?: {
    retention_milestones: any;
    significant_drops: any[];
    video_stats: any;
  };
}

// ========== API Functions ==========

/**
 * Trigger analytics sync for a channel
 */
export async function syncChannelAnalytics(
  channelId: number,
  daysBack: number = 30
): Promise<any> {
  const res = await fetch(`${API_URL}/api/analytics/sync/${channelId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ days_back: daysBack }),
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to sync analytics');
  }
  return await res.json();
}

/**
 * Get comprehensive analytics for a single video
 */
export async function getVideoAnalytics(videoId: number): Promise<VideoAnalytics> {
  const res = await fetch(`${API_URL}/api/analytics/video/${videoId}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch video analytics');
  }
  return await res.json();
}

/**
 * Get retention curve data for a video
 */
export async function getRetentionCurve(videoId: number): Promise<RetentionCurve> {
  const res = await fetch(`${API_URL}/api/analytics/retention/${videoId}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch retention curve');
  }
  return await res.json();
}

/**
 * Get traffic sources for a video
 */
export async function getTrafficSources(videoId: number): Promise<TrafficSourcesResponse> {
  const res = await fetch(`${API_URL}/api/analytics/traffic-sources/${videoId}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch traffic sources');
  }
  return await res.json();
}

/**
 * Get channel analytics summary
 */
export async function getChannelSummary(channelId: number): Promise<ChannelSummary> {
  const res = await fetch(`${API_URL}/api/analytics/channel/${channelId}/summary`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch channel summary');
  }
  return await res.json();
}

/**
 * Get duration vs retention analysis
 */
export async function getDurationAnalysis(channelId: number): Promise<DurationAnalysis> {
  const res = await fetch(`${API_URL}/api/analytics/pattern-analysis/retention-by-duration/${channelId}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch duration analysis');
  }
  return await res.json();
}

/**
 * Get hook effectiveness analysis
 */
export async function getHookAnalysis(channelId: number): Promise<HookAnalysis> {
  const res = await fetch(`${API_URL}/api/analytics/pattern-analysis/hook-effectiveness/${channelId}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch hook analysis');
  }
  return await res.json();
}

/**
 * Get traffic source performance analysis
 */
export async function getTrafficSourceAnalysis(channelId: number): Promise<TrafficSourceAnalysis> {
  const res = await fetch(`${API_URL}/api/analytics/pattern-analysis/traffic-sources/${channelId}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch traffic source analysis');
  }
  return await res.json();
}

/**
 * Get optimal posting time analysis
 */
export async function getPostingTimeAnalysis(channelId: number): Promise<PostingTimeAnalysis> {
  const res = await fetch(`${API_URL}/api/analytics/pattern-analysis/posting-time/${channelId}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch posting time analysis');
  }
  return await res.json();
}

/**
 * Get engagement patterns analysis
 */
export async function getEngagementAnalysis(channelId: number): Promise<EngagementAnalysis> {
  const res = await fetch(`${API_URL}/api/analytics/pattern-analysis/engagement/${channelId}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch engagement analysis');
  }
  return await res.json();
}

/**
 * Get AI-powered content recommendations
 */
export async function getContentRecommendations(channelId: number): Promise<ContentRecommendations> {
  const res = await fetch(`${API_URL}/api/analytics/recommendations/${channelId}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch recommendations');
  }
  return await res.json();
}

/**
 * Get comprehensive AI-powered insights (cached for 24h)
 */
export async function getComprehensiveInsights(
  channelId: number,
  forceRefresh: boolean = false
): Promise<ComprehensiveInsights> {
  const res = await fetch(
    `${API_URL}/api/insights/comprehensive/${channelId}?force_refresh=${forceRefresh}`,
    { credentials: 'include' }
  );
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch comprehensive insights');
  }
  return await res.json();
}

/**
 * Get performance drivers analysis with LLM insights
 */
export async function getPerformanceDrivers(
  channelId: number,
  useLlm: boolean = true
): Promise<PerformanceDrivers> {
  const res = await fetch(
    `${API_URL}/api/insights/performance-drivers/${channelId}?use_llm=${useLlm}`,
    { credentials: 'include' }
  );
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch performance drivers');
  }
  return await res.json();
}

/**
 * Get retention analysis for a specific video with LLM insights
 */
export async function getVideoRetentionAnalysis(
  videoId: number,
  useLlm: boolean = true
): Promise<RetentionAnalysis> {
  const res = await fetch(
    `${API_URL}/api/insights/retention-analysis/${videoId}?use_llm=${useLlm}`,
    { credentials: 'include' }
  );
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to fetch retention analysis');
  }
  return await res.json();
}
