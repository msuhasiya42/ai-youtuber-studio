
import React, { useState } from 'react';
import { YoutubeIcon } from './icons';
import { getGoogleOAuthUrl } from '../services/backendApi';

interface OnboardingProps {
  onConnect: () => void;
}

const Onboarding: React.FC<OnboardingProps> = ({ onConnect }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  async function handleConnect() {
    setLoading(true);
    setError(null);
    try {
      const url = await getGoogleOAuthUrl();
      window.location.href = url;
    } catch (e:any) {
      setError(e.message || 'Failed to initiate OAuth');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-background to-gray-900 p-4">
      <div className="text-center max-w-2xl">
        <h1 className="text-4xl md:text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-600 mb-4">
          AI YouTuber Studio
        </h1>
        <p className="text-lg md:text-xl text-text-secondary mb-8">
          Connect your channel to unlock AI-powered insights, generate content ideas, and get full scripts to grow your audience.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={handleConnect}
            className="group flex items-center justify-center gap-3 px-6 py-2 bg-primary text-white font-semibold rounded-lg shadow-lg hover:bg-primary-hover transition-all duration-300 transform hover:scale-105 disabled:opacity-50"
            disabled={loading}
          >
            <YoutubeIcon className="w-16 h-16" />
            {loading ? 'Loading…' : 'Connect with YouTube'}
          </button>
        </div>
        {error && <div className="mt-4 text-red-500 font-semibold">{error}</div>}
        <p className="text-sm text-gray-500 mt-8">
            By connecting, you agree to our terms of service. We use the YouTube Data API to access your channel's public and private analytics data in a read-only fashion.
        </p>
      </div>
    </div>
  );
};

export default Onboarding;
