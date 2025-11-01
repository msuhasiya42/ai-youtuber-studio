import React, { useState, useCallback, useEffect } from 'react';
import Onboarding from './components/Onboarding';
import Dashboard from './components/Dashboard';
import AllVideosPage from './components/AllVideosPage';
import ContentStudio from './pages/ContentStudio';
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

type View = 'onboarding' | 'dashboard' | 'allVideos' | 'contentStudio';

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
  const [currentView, setCurrentView] = useState<View>('onboarding');
  const [authChecked, setAuthChecked] = useState(false);
  const [channelData, setChannelData] = useState<ChannelData | null>(null); // Add channelData state

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
              setChannelData(data); // Store fetched channel data
              setCurrentView('dashboard');
            },
            (error) => { // Catch errors and set channelData to null
              console.error("Error fetching channel after OAuth:", error);
              setChannelData(null); // Clear channel data on error
              setCurrentView('onboarding');
            }
          ).finally(() => setAuthChecked(true));
        } else {
          setCurrentView('onboarding');
          setAuthChecked(true);
        }
      });
      return;
    }
    // Try to auto-login if already connected
    getChannel().then(
      (data) => { // Receive data here
        setChannelData(data); // Store fetched channel data
        setCurrentView('dashboard');
        setAuthChecked(true);
      },
      (error) => { // Catch errors and set channelData to null
        console.error("Error auto-fetching channel:", error);
        setChannelData(null); // Clear channel data on error
        setCurrentView('onboarding');
        setAuthChecked(true);
      }
    );
  }, []);

  const handleConnect = useCallback(() => {
    // This is now handled by the OAuth flow.
    // If we're redirected back from OAuth, channel data should be fetched.
    // So, we just ensure it transitions to dashboard here.
    setCurrentView('dashboard');
  }, []);
  
  const handleDisconnect = useCallback(() => {
    setChannelData(null); // Clear channel data on disconnect
    setCurrentView('onboarding');
  }, []);

  const handleNavigateToAllVideos = useCallback(() => {
    setCurrentView('allVideos');
  }, []);

  const handleNavigateToDashboard = useCallback(() => {
    setCurrentView('dashboard');
  }, []);

  const handleNavigateToContentStudio = useCallback(() => {
    setCurrentView('contentStudio');
  }, []);

  const handleChannelDataUpdate = useCallback((updatedChannel: ChannelData) => {
    setChannelData(updatedChannel); // Update App's state with refreshed channel data
  }, []);

  const renderView = () => {
    if (!authChecked) return <div className="w-full min-h-screen flex items-center justify-center">Checking authentication…</div>;
    switch(currentView) {
      case 'onboarding':
        return <Onboarding onConnect={handleConnect} />;
      case 'dashboard':
        return <Dashboard channelData={channelData} onDisconnect={handleDisconnect} onSeeAll={handleNavigateToAllVideos} onChannelDataUpdate={handleChannelDataUpdate} onOpenContentStudio={handleNavigateToContentStudio} />; // Pass onChannelDataUpdate
      case 'allVideos':
        return <AllVideosPage onBack={handleNavigateToDashboard} />;
      case 'contentStudio':
        return channelData ? (
          <ContentStudio channelId={channelData.id} channelName={channelData.name} />
        ) : (
          <div className="w-full min-h-screen flex items-center justify-center">Loading...</div>
        );
      default:
        // Fallback to onboarding view
        return <Onboarding onConnect={handleConnect} />;
    }
  };

  return (
    <div className="min-h-screen w-full">
      {renderView()}
    </div>
  );
};

export default App;