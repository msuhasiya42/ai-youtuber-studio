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
