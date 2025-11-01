const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export interface PatternAnalysis {
  channel_name: string;
  videos_analyzed: number;
  title_patterns: {
    common_keywords: Array<{word: string; count: number}>;
    average_length: number;
    patterns: Record<string, number>;
    sample_titles: string[];
  };
  duration_patterns: {
    average_seconds: number;
    average_minutes: number;
    min_duration: number;
    max_duration: number;
    duration_range: string;
  };
  engagement_patterns: {
    average_views: number;
    average_likes: number;
    engagement_rate: number;
    total_videos_analyzed: number;
  };
  content_themes: string[];
  recommendations: string[];
}

export interface GeneratedScript {
  status: string;
  script: {
    title_suggestion: string;
    hook: string;
    introduction: string;
    body: Array<{timestamp: string; content: string}>;
    conclusion: string;
    visual_cues: string[];
    estimated_retention_points: string[];
  };
  topic: string;
  format: string;
  duration_minutes: number;
  context_used: number;
}

export interface TitleSuggestion {
  title: string;
  score: number;
  predicted_ctr: string;
  grade: string;
  factors: Array<{factor: string; points: number}>;
}

export async function analyzeChannelPatterns(channelId: number, topN: number = 10): Promise<PatternAnalysis> {
  const res = await fetch(`${API_URL}/api/content-studio/analyze-patterns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ channel_id: channelId, top_n: topN })
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to analyze patterns');
  }

  return await res.json();
}

export async function generateScript(
  channelId: number,
  topic: string,
  tone?: string,
  minutes?: number,
  videoFormat?: string
): Promise<GeneratedScript> {
  const res = await fetch(`${API_URL}/api/content-studio/generate-script`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      channel_id: channelId,
      topic,
      tone,
      minutes: minutes || 8,
      video_format: videoFormat || 'standard'
    })
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to generate script');
  }

  return await res.json();
}

export async function generateTitles(
  channelId: number,
  topic: string,
  count: number = 5
): Promise<{topic: string; titles: TitleSuggestion[]; count: number}> {
  const res = await fetch(`${API_URL}/api/content-studio/generate-titles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      channel_id: channelId,
      topic,
      count
    })
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to generate titles');
  }

  return await res.json();
}

export async function syncVideos(channelId: number, limit: number = 50) {
  const res = await fetch(`${API_URL}/api/channels/${channelId}/sync-videos?limit=${limit}`, {
    method: 'POST',
    credentials: 'include'
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to sync videos');
  }

  return await res.json();
}

export async function processVideoPipeline(videoId: number) {
  const res = await fetch(`${API_URL}/api/content-studio/process-video-pipeline/${videoId}`, {
    method: 'POST',
    credentials: 'include'
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to process video');
  }

  return await res.json();
}

export async function getChannelInsights(channelId: number) {
  const res = await fetch(`${API_URL}/api/content-studio/insights/${channelId}`, {
    credentials: 'include'
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to fetch insights');
  }

  return await res.json();
}
