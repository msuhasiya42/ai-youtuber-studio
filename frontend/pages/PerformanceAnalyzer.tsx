import React, { useState, useEffect } from 'react';
import { analyzeChannelPatterns, type PatternAnalysis } from '../services/contentStudioApi';

interface PerformanceAnalyzerProps {
  channelId: number;
  channelName: string;
}

const PerformanceAnalyzer: React.FC<PerformanceAnalyzerProps> = ({ channelId, channelName }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patterns, setPatterns] = useState<PatternAnalysis | null>(null);

  const handleAnalyzePatterns = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await analyzeChannelPatterns(channelId, 10);
      setPatterns(result);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze patterns');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Auto-analyze on mount if we don't have patterns yet
    if (!patterns) {
      handleAnalyzePatterns();
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Performance Analyzer</h1>
          <p className="text-gray-400">Channel: {channelName}</p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && !patterns && (
          <div className="text-center py-12">
            <p className="text-gray-400">Analyzing your top videos...</p>
          </div>
        )}

        {/* Performance Insights */}
        {patterns && (
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-bold mb-4">Performance Patterns</h2>
              <p className="text-gray-400 mb-6">
                Analysis of your top {patterns.videos_analyzed} performing videos
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-indigo-900/30 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Avg. Views</p>
                  <p className="text-2xl font-bold">{patterns.engagement_patterns.average_views.toLocaleString()}</p>
                </div>
                <div className="bg-indigo-900/30 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Engagement Rate</p>
                  <p className="text-2xl font-bold">{patterns.engagement_patterns.engagement_rate}%</p>
                </div>
                <div className="bg-indigo-900/30 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Optimal Duration</p>
                  <p className="text-2xl font-bold">{patterns.duration_patterns.average_minutes} min</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-xl font-bold mb-4">Top Keywords</h3>
              <div className="flex flex-wrap gap-2">
                {patterns.title_patterns.common_keywords.slice(0, 10).map((kw, idx) => (
                  <span key={idx} className="bg-indigo-900/40 px-3 py-1 rounded-full text-sm">
                    {kw.word} ({kw.count})
                  </span>
                ))}
              </div>
            </div>

            {patterns.content_themes && patterns.content_themes.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-6">
                <h3 className="text-xl font-bold mb-4">Content Themes</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {patterns.content_themes.map((theme, idx) => (
                    <div key={idx} className="bg-gray-700/50 px-4 py-3 rounded-lg">
                      {theme}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-xl font-bold mb-4">Recommendations</h3>
              <ul className="space-y-2">
                {patterns.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="text-green-400 mt-1">✓</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>

            <button
              onClick={handleAnalyzePatterns}
              disabled={loading}
              className="w-full bg-gray-700 hover:bg-gray-600 text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Analyzing...' : 'Refresh Analysis'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PerformanceAnalyzer;
