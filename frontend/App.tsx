import React, { useState, useCallback, useEffect } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import Onboarding from './components/Onboarding';
import Dashboard from './components/Dashboard';
import AllVideosPage from './components/AllVideosPage';
import ContentStudio from './pages/ContentStudio';
import PerformanceAnalyzer from './pages/PerformanceAnalyzer';
import VideoProcessingDashboard from './pages/VideoProcessingDashboard';
import ChannelAnalyticsDashboard from './pages/ChannelAnalyticsDashboard';
import VideoAnalyticsDetail from './pages/VideoAnalyticsDetail';
import Navbar from './components/Navbar';
import { getChannel } from './services/backendApi';

// Utility to parse code out of url
function getQueryParam(name: string): string | null {
  return new URLSearchParams(window.location.search).get(name);
}

// Call backend to finish oauth (exchange code)
async function completeOAuth(code: string): Promise<boolean> {
  const resp = await fetch(`/api/auth/oauth/google/callback?code=${encodeURIComponent(code)}`, {
    credentials: 'include',
  });
  return resp.ok;
}

interface ChannelData {
  id: number;
  youtube_channel_id: string;
  name: string;
  avatar_url?: string;
  subscribers: number;
  verified: boolean;
  total_views: number;
  total_watch_hours: number;
}

const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [authChecked, setAuthChecked] = useState(false);
  const [channelData, setChannelData] = useState<ChannelData | null>(null);

  useEffect(() => {
    // Detect if redirected back from Google after OAuth
    const code = getQueryParam('code');
    if (code) {
      completeOAuth(code).then(success => {
        if (success) {
          window.history.replaceState({}, document.title, '/');
          // After successful OAuth, immediately try to fetch channel data
          getChannel().then(
            (data) => {
              setChannelData(data);
              navigate('/dashboard');
            },
            (error) => {
              console.error("Error fetching channel after OAuth:", error);
              setChannelData(null);
              navigate('/');
            }
          ).finally(() => setAuthChecked(true));
        } else {
          navigate('/');
          setAuthChecked(true);
        }
      });
      return;
    }
    // Try to auto-login if already connected
    getChannel().then(
      (data) => {
        setChannelData(data);
        // Only navigate if not already on a protected route
        if (location.pathname === '/') {
          navigate('/dashboard');
        }
        setAuthChecked(true);
      },
      (error) => {
        console.error("Error auto-fetching channel:", error);
        setChannelData(null);
        navigate('/');
        setAuthChecked(true);
      }
    );
  }, [navigate, location.pathname]);

  const handleConnect = useCallback(() => {
    navigate('/dashboard');
  }, [navigate]);

  const handleDisconnect = useCallback(() => {
    setChannelData(null);
    navigate('/');
  }, [navigate]);

  const handleNavigateToAllVideos = useCallback(() => {
    navigate('/all-videos');
  }, [navigate]);

  const handleNavigateToDashboard = useCallback(() => {
    navigate('/dashboard');
  }, [navigate]);

  const handleNavigateToContentStudio = useCallback(() => {
    navigate('/content-studio');
  }, [navigate]);

  const handleChannelDataUpdate = useCallback((updatedChannel: ChannelData) => {
    setChannelData(updatedChannel);
  }, []);

  if (!authChecked) {
    return <div className="w-full min-h-screen flex items-center justify-center">Checking authentication…</div>;
  }

  return (
    <div className="min-h-screen w-full">
      {location.pathname !== '/' && <Navbar />}
      <Routes>
        <Route path="/" element={<Onboarding onConnect={handleConnect} />} />
        <Route
          path="/dashboard"
          element={
            <Dashboard
              channelData={channelData}
              onDisconnect={handleDisconnect}
              onSeeAll={handleNavigateToAllVideos}
              onChannelDataUpdate={handleChannelDataUpdate}
              onOpenContentStudio={handleNavigateToContentStudio}
            />
          }
        />
        <Route
          path="/all-videos"
          element={<AllVideosPage onBack={handleNavigateToDashboard} />}
        />
        <Route
          path="/content-studio"
          element={
            channelData ? (
              <ContentStudio channelId={channelData.id} channelName={channelData.name} />
            ) : (
              <div className="w-full min-h-screen flex items-center justify-center">Loading...</div>
            )
          }
        />
        <Route
          path="/analyzer"
          element={
            channelData ? (
              <PerformanceAnalyzer channelId={channelData.id} channelName={channelData.name} />
            ) : (
              <div className="w-full min-h-screen flex items-center justify-center">Loading...</div>
            )
          }
        />
        <Route
          path="/processing-status"
          element={
            channelData ? (
              <VideoProcessingDashboard channelId={channelData.id} channelName={channelData.name} />
            ) : (
              <div className="w-full min-h-screen flex items-center justify-center">Loading...</div>
            )
          }
        />
        <Route
          path="/analytics"
          element={
            channelData ? (
              <ChannelAnalyticsDashboard channelId={channelData.id} channelName={channelData.name} />
            ) : (
              <div className="w-full min-h-screen flex items-center justify-center">Loading...</div>
            )
          }
        />
        <Route path="/video/:videoId/analytics" element={<VideoAnalyticsDetail />} />
      </Routes>
    </div>
  );
};

export default App;