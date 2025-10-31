import React, { useState, useCallback, useEffect } from 'react';
import Onboarding from './components/Onboarding';
import Dashboard from './components/Dashboard';
import AllVideosPage from './components/AllVideosPage';
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

type View = 'onboarding' | 'dashboard' | 'allVideos';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<View>('onboarding');
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    // Detect if redirected back from Google after OAuth
    const code = getQueryParam('code');
    if (code) {
      completeOAuth(code).then(success => {
        if (success) {
          window.history.replaceState({}, document.title, '/');
          setCurrentView('dashboard');
        } else {
          setCurrentView('onboarding');
        }
        setAuthChecked(true);
      });
      return;
    }
    // Try to auto-login if already connected
    getChannel().then(
      () => {
        setCurrentView('dashboard');
        setAuthChecked(true);
      },
      () => {
        setCurrentView('onboarding');
        setAuthChecked(true);
      }
    );
  }, []);

  const handleConnect = useCallback(() => {
    setCurrentView('dashboard');
  }, []);
  
  const handleDisconnect = useCallback(() => {
    setCurrentView('onboarding');
  }, []);

  const handleNavigateToAllVideos = useCallback(() => {
    setCurrentView('allVideos');
  }, []);

  const handleNavigateToDashboard = useCallback(() => {
    setCurrentView('dashboard');
  }, []);

  const renderView = () => {
    if (!authChecked) return <div className="w-full min-h-screen flex items-center justify-center">Checking authentication…</div>;
    switch(currentView) {
      case 'onboarding':
        return <Onboarding onConnect={handleConnect} />;
      case 'dashboard':
        return <Dashboard onDisconnect={handleDisconnect} onSeeAll={handleNavigateToAllVideos} />;
      case 'allVideos':
        return <AllVideosPage onBack={handleNavigateToDashboard} />;
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