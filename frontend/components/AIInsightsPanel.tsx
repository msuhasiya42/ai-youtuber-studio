import React, { useState, useEffect } from 'react';
import {
  getPerformanceDrivers,
  getContentRecommendations,
  type PerformanceDrivers,
  type ContentRecommendations,
} from '../services/analyticsApi';

interface AIInsightsPanelProps {
  channelId: number;
}

const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({ channelId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [performanceDrivers, setPerformanceDrivers] = useState<PerformanceDrivers | null>(null);
  const [recommendations, setRecommendations] = useState<ContentRecommendations | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadInsights();
  }, [channelId]);

  const loadInsights = async (useLlm: boolean = true) => {
    setLoading(true);
    setError(null);

    try {
      const [drivers, recs] = await Promise.all([
        getPerformanceDrivers(channelId, useLlm),
        getContentRecommendations(channelId),
      ]);

      setPerformanceDrivers(drivers);
      setRecommendations(recs);
    } catch (err: any) {
      setError(err.message || 'Failed to load AI insights');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadInsights(true);
  };

  if (loading && !performanceDrivers) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Generating AI insights...</p>
            <p className="text-sm text-gray-500 mt-2">This may take a moment</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded">
          <p className="font-semibold mb-1">Error loading AI insights</p>
          <p className="text-sm">{error}</p>
          <button
            onClick={() => loadInsights()}
            className="mt-3 bg-red-700 hover:bg-red-600 px-4 py-2 rounded text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <span>🤖</span>
              <span>AI-Powered Insights</span>
            </h2>
            {performanceDrivers && (
              <p className="text-sm text-gray-400 mt-1">
                Based on {performanceDrivers.videos_analyzed} top-performing videos
              </p>
            )}
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {refreshing ? (
              <>
                <span className="animate-spin">⟳</span>
                <span>Refreshing...</span>
              </>
            ) : (
              <>
                <span>⟳</span>
                <span>Refresh Insights</span>
              </>
            )}
          </button>
        </div>

        {!performanceDrivers?.use_llm && (
          <div className="bg-yellow-900/20 border border-yellow-500/30 rounded p-3 mb-4">
            <p className="text-sm text-yellow-300">
              💡 LLM insights are disabled. Enable LLM for deeper narrative insights.
            </p>
          </div>
        )}
      </div>

      {/* Performance Drivers */}
      {performanceDrivers && performanceDrivers.use_llm && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span>🎯</span>
            <span>What Makes Your Videos Succeed</span>
          </h3>

          {performanceDrivers.key_success_factors && (
            <div className="mb-6">
              <h4 className="font-semibold text-green-400 mb-3">Key Success Factors</h4>
              <ul className="space-y-2">
                {performanceDrivers.key_success_factors.map((factor, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="text-green-400 mt-1">✓</span>
                    <span className="text-gray-300">{factor}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {performanceDrivers.common_patterns && (
            <div className="mb-6">
              <h4 className="font-semibold text-blue-400 mb-3">Common Patterns</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {performanceDrivers.common_patterns.map((pattern, idx) => (
                  <div key={idx} className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3">
                    <p className="text-sm text-gray-300">{pattern}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {performanceDrivers.optimization_opportunities && (
            <div className="mb-6">
              <h4 className="font-semibold text-purple-400 mb-3">Optimization Opportunities</h4>
              <ul className="space-y-2">
                {performanceDrivers.optimization_opportunities.map((opp, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="text-purple-400 mt-1">→</span>
                    <span className="text-gray-300">{opp}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {performanceDrivers.recommendations && (
            <div className="bg-indigo-900/20 border border-indigo-500/30 rounded-lg p-4">
              <h4 className="font-semibold text-indigo-300 mb-3">Action Items</h4>
              <ul className="space-y-2">
                {performanceDrivers.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="text-indigo-400 mt-1">📌</span>
                    <span className="text-gray-300">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Content Recommendations */}
      {recommendations && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span>💡</span>
            <span>Content Recommendations</span>
          </h3>

          {recommendations.top_opportunities && recommendations.top_opportunities.length > 0 && (
            <div className="mb-6 bg-gradient-to-r from-indigo-900/30 to-purple-900/30 border border-indigo-500/30 rounded-lg p-4">
              <h4 className="font-semibold text-indigo-300 mb-3">🚀 Top Opportunities</h4>
              <ul className="space-y-2">
                {recommendations.top_opportunities.map((opp, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="text-yellow-400 mt-1">⭐</span>
                    <span className="text-gray-300 font-medium">{opp}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {recommendations.recommendations && (
            <div className="space-y-4">
              {recommendations.recommendations.map((rec, idx) => {
                const priorityColors = {
                  high: 'border-red-500/30 bg-red-900/20',
                  medium: 'border-yellow-500/30 bg-yellow-900/20',
                  low: 'border-blue-500/30 bg-blue-900/20',
                };
                const priorityLabels = {
                  high: '🔴 High Priority',
                  medium: '🟡 Medium Priority',
                  low: '🔵 Low Priority',
                };

                return (
                  <div
                    key={idx}
                    className={`rounded-lg p-4 border ${
                      priorityColors[rec.priority as keyof typeof priorityColors] ||
                      priorityColors.low
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-semibold text-white">{rec.category}</h4>
                      <span className="text-xs px-2 py-1 rounded-full bg-gray-700">
                        {priorityLabels[rec.priority as keyof typeof priorityLabels] ||
                          rec.priority}
                      </span>
                    </div>
                    <ul className="space-y-2">
                      {rec.suggestions.map((suggestion, sIdx) => (
                        <li key={sIdx} className="flex items-start gap-2">
                          <span className="text-gray-400 mt-1">•</span>
                          <span className="text-gray-300 text-sm">{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AIInsightsPanel;
