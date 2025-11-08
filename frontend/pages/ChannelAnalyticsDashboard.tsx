import React, { useState, useEffect } from 'react';
import {
  getChannelSummary,
  syncChannelAnalytics,
  type ChannelSummary,
} from '../services/analyticsApi';
import PatternAnalysisPanel from '../components/PatternAnalysisPanel';
import AIInsightsPanel from '../components/AIInsightsPanel';

interface ChannelAnalyticsDashboardProps {
  channelId: number;
  channelName: string;
}

const ChannelAnalyticsDashboard: React.FC<ChannelAnalyticsDashboardProps> = ({
  channelId,
  channelName,
}) => {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ChannelSummary | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'patterns' | 'ai-insights'>('overview');

  useEffect(() => {
    loadSummary();
  }, [channelId]);

  const loadSummary = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getChannelSummary(channelId);
      setSummary(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load channel analytics');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncAnalytics = async () => {
    setSyncing(true);
    setError(null);

    try {
      await syncChannelAnalytics(channelId, 90);
      // Wait a bit for sync to process
      setTimeout(() => {
        loadSummary();
        setSyncing(false);
      }, 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to sync analytics');
      setSyncing(false);
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'patterns', label: 'Pattern Analysis', icon: '🔍' },
    { id: 'ai-insights', label: 'AI Insights', icon: '🤖' },
  ] as const;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold mb-2">Analytics Dashboard</h1>
              <p className="text-gray-400">Channel: {channelName}</p>
            </div>
            <button
              onClick={handleSyncAnalytics}
              disabled={syncing}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {syncing ? (
                <>
                  <span className="animate-spin">⟳</span>
                  <span>Syncing...</span>
                </>
              ) : (
                <>
                  <span>⟳</span>
                  <span>Sync Analytics</span>
                </>
              )}
            </button>
          </div>

          {syncing && (
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3">
              <p className="text-sm text-blue-300">
                📡 Syncing analytics data from YouTube... This may take a few minutes for all
                videos.
              </p>
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 rounded-lg font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Loading State */}
        {loading && !summary ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading analytics data...</p>
          </div>
        ) : null}

        {/* Overview Tab */}
        {activeTab === 'overview' && summary && (
          <div className="space-y-6">
            {/* Summary Stats */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-bold mb-6">Channel Performance Summary</h2>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Total Videos</p>
                  <p className="text-3xl font-bold text-white">{summary.total_videos}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {summary.total_videos_analyzed} analyzed
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Total Views</p>
                  <p className="text-3xl font-bold text-indigo-400">
                    {summary.summary?.total_views?.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Avg: {summary.summary?.avg_views_per_video?.toLocaleString()}/video
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Watch Time</p>
                  <p className="text-3xl font-bold text-purple-400">
                    {summary.summary?.total_watch_time_hours?.toLocaleString()}h
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {summary.summary?.total_watch_time_minutes?.toLocaleString()} minutes
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Subscribers Gained</p>
                  <p className="text-3xl font-bold text-green-400">
                    +{summary.summary?.total_subscribers_gained?.toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-indigo-900/30 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Avg Retention</p>
                  <p className="text-2xl font-bold text-indigo-400">
                    {summary.summary?.avg_retention_percentage?.toFixed(1)}%
                  </p>
                </div>
                <div className="bg-purple-900/30 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Avg Engagement</p>
                  <p className="text-2xl font-bold text-purple-400">
                    {summary.summary?.avg_engagement_rate?.toFixed(2)}%
                  </p>
                </div>
                <div className="bg-blue-900/30 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Avg Hook Strength</p>
                  <p className="text-2xl font-bold text-blue-400">
                    {summary.summary?.avg_hook_strength
                      ? `${summary.summary?.avg_hook_strength?.toFixed(1)}%`
                      : 'N/A'}
                  </p>
                </div>
              </div>
            </div>

            {/* Top Performers */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-xl font-bold mb-4">Top Performing Videos</h3>
              <div className="space-y-3">
                {summary.top_performers?.map((video, idx) => (
                  <div
                    key={video.video_id}
                    className="bg-gray-700/50 rounded-lg p-4 hover:bg-gray-700 transition-colors"
                  >
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center font-bold">
                        {idx + 1}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold mb-2">{video.title}</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                          <div>
                            <span className="text-gray-400">Views:</span>{' '}
                            <span className="text-white font-mono">
                              {video.views.toLocaleString()}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-400">Retention:</span>{' '}
                            <span className="text-white font-mono">
                              {video?.retention?.toFixed(1) || 'N/A'}%
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-400">Engagement:</span>{' '}
                            <span className="text-white font-mono">
                              {video.engagement_rate.toFixed(2)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-400">Hook:</span>{' '}
                            <span className="text-white font-mono">
                              {video.hook_strength?.toFixed(1) || 'N/A'}%
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {summary.total_videos_analyzed === 0 && (
              <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-6 text-center">
                <p className="text-lg text-yellow-300 mb-2">
                  📊 No analytics data available yet
                </p>
                <p className="text-sm text-gray-400 mb-4">
                  Click "Sync Analytics" to fetch data from YouTube Analytics API
                </p>
                <button
                  onClick={handleSyncAnalytics}
                  disabled={syncing}
                  className="bg-yellow-600 hover:bg-yellow-700 text-white px-6 py-2 rounded-lg transition-colors disabled:opacity-50"
                >
                  Sync Now
                </button>
              </div>
            )}
          </div>
        )}

        {/* Pattern Analysis Tab */}
        {activeTab === 'patterns' && <PatternAnalysisPanel channelId={channelId} />}

        {/* AI Insights Tab */}
        {activeTab === 'ai-insights' && <AIInsightsPanel channelId={channelId} />}
      </div>
    </div>
  );
};

export default ChannelAnalyticsDashboard;
