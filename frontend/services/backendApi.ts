const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export async function getGoogleOAuthUrl(): Promise<string> {
  const res = await fetch(`${API_URL}/api/auth/oauth/google/url`);
  if (!res.ok) throw new Error('Failed to get OAuth URL');
  const data = await res.json();
  return data.url;
}

// Poll endpoint to check if user is fully connected/session, if your backend provides
// Or fetch channel info directly if session cookie exists
export async function getChannel(): Promise<any> {
  const res = await fetch(`${API_URL}/api/channels/me`, { credentials: 'include' });
  if (!res.ok) throw new Error('Not connected');
  return await res.json();
}

// NEW FUNCTION: Refresh channel data from backend
export async function refreshChannelData(channelId: number): Promise<any> {
  const res = await fetch(`${API_URL}/api/channels/${channelId}/refresh`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to refresh channel data');
  }
  return await res.json();
}

// Sync videos from YouTube to database
export async function syncChannelVideos(channelId: number, limit: number = 50): Promise<any> {
  const res = await fetch(`${API_URL}/api/channels/${channelId}/sync-videos?limit=${limit}`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to sync videos');
  }
  return await res.json();
}