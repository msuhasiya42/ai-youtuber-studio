import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getVideoAnalytics,
  getRetentionCurve,
  getTrafficSources,
  getVideoRetentionAnalysis,
  type VideoAnalytics,
  type RetentionCurve,
  type TrafficSourcesResponse,
  type RetentionAnalysis,
} from '../services/analyticsApi';
import RetentionCurveChart from '../components/RetentionCurveChart';
import TrafficSourcesChart from '../components/TrafficSourcesChart';

const VideoAnalyticsDetail: React.FC = () => {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [videoAnalytics, setVideoAnalytics] = useState<VideoAnalytics | null>(null);
  const [retentionCurve, setRetentionCurve] = useState<RetentionCurve | null>(null);
  const [trafficSources, setTrafficSources] = useState<TrafficSourcesResponse | null>(null);
  const [aiInsights, setAiInsights] = useState<RetentionAnalysis | null>(null);

  const [loadingAI, setLoadingAI] = useState(false);

  useEffect(() => {
    if (videoId) {
      loadVideoData();
    }
  }, [videoId]);

  const loadVideoData = async () => {
    setLoading(true);
    setError(null);

    try {
      const id = parseInt(videoId!);

      // Load basic analytics and traffic sources in parallel
      const [analytics, traffic] = await Promise.all([
        getVideoAnalytics(id),
        getTrafficSources(id),
      ]);

      setVideoAnalytics(analytics);
      setTrafficSources(traffic);

      // Try to load retention curve (may not be available for all videos)
      try {
        const retention = await getRetentionCurve(id);
        setRetentionCurve(retention);
      } catch (err) {
        console.log('Retention curve not available for this video');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load video analytics');
    } finally {
      setLoading(false);
    }
  };

  const loadAIInsights = async () => {
    if (!videoId) return;

    setLoadingAI(true);
    try {
      const insights = await getVideoRetentionAnalysis(parseInt(videoId), true);
      setAiInsights(insights);
    } catch (err: any) {
      console.error('Failed to load AI insights:', err);
    } finally {
      setLoadingAI(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-6">
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading video analytics...</p>
        </div>
      </div>
    );
  }

  if (error || !videoAnalytics) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-6">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={() => navigate(-1)}
            className="mb-6 text-gray-400 hover:text-white transition-colors"
          >
            ← Back
          </button>
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded">
            {error || 'Video not found'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <button
          onClick={() => navigate(-1)}
          className="mb-6 text-gray-400 hover:text-white transition-colors flex items-center gap-2"
        >
          <span>←</span>
          <span>Back</span>
        </button>

        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">{videoAnalytics.title}</h1>
          <p className="text-gray-400 text-sm">Video ID: {videoAnalytics.youtube_video_id}</p>
          {videoAnalytics.last_analytics_sync_at && (
            <p className="text-gray-500 text-xs mt-1">
              Last synced: {new Date(videoAnalytics.last_analytics_sync_at).toLocaleString()}
            </p>
          )}
        </div>

        {/* Main Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400 mb-1">Views</p>
            <p className="text-2xl font-bold text-white">
              {videoAnalytics.views.toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400 mb-1">Likes</p>
            <p className="text-2xl font-bold text-green-400">
              {videoAnalytics.likes.toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400 mb-1">Comments</p>
            <p className="text-2xl font-bold text-blue-400">
              {videoAnalytics.comments.toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400 mb-1">Shares</p>
            <p className="text-2xl font-bold text-purple-400">
              {videoAnalytics.shares.toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400 mb-1">Engagement</p>
            <p className="text-2xl font-bold text-indigo-400">
              {videoAnalytics.engagement_rate.toFixed(2)}%
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400 mb-1">Sub Gained</p>
            <p className="text-2xl font-bold text-yellow-400">
              +{videoAnalytics.subscribers_gained}
            </p>
          </div>
        </div>

        {/* Advanced Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400 mb-1">Avg View Duration</p>
            <p className="text-xl font-bold text-white">
              {videoAnalytics.average_view_duration_seconds
                ? `${Math.floor(videoAnalytics.average_view_duration_seconds / 60)}m ${
                    videoAnalytics.average_view_duration_seconds % 60
                  }s`
                : 'N/A'}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {videoAnalytics.average_view_percentage
                ? `${videoAnalytics.average_view_percentage.toFixed(1)}% retention`
                : ''}
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400 mb-1">Watch Time</p>
            <p className="text-xl font-bold text-white">
              {videoAnalytics.estimated_minutes_watched
                ? `${videoAnalytics.estimated_minutes_watched.toLocaleString()} min`
                : 'N/A'}
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400 mb-1">First 24h Views</p>
            <p className="text-xl font-bold text-white">
              {videoAnalytics.first_24h_views
                ? videoAnalytics.first_24h_views.toLocaleString()
                : 'N/A'}
            </p>
          </div>
        </div>

        {/* Retention Curve */}
        {retentionCurve && (
          <div className="mb-8">
            <RetentionCurveChart data={retentionCurve} />
          </div>
        )}

        {/* AI Insights */}
        {retentionCurve && (
          <div className="mb-8">
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold flex items-center gap-2">
                  <span>🤖</span>
                  <span>AI Retention Insights</span>
                </h3>
                <button
                  onClick={loadAIInsights}
                  disabled={loadingAI}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50 text-sm"
                >
                  {loadingAI ? 'Analyzing...' : aiInsights ? 'Refresh' : 'Generate Insights'}
                </button>
              </div>

              {loadingAI && (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto mb-3"></div>
                  <p className="text-sm text-gray-400">Generating AI insights...</p>
                </div>
              )}

              {aiInsights && aiInsights.retention_insights && (
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold text-green-400 mb-2">Overall Performance</h4>
                    <p className="text-gray-300">{aiInsights.retention_insights.overall_performance}</p>
                  </div>

                  {aiInsights.retention_insights.critical_moments.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-red-400 mb-2">Critical Moments</h4>
                      <ul className="space-y-2">
                        {aiInsights.retention_insights.critical_moments.map((moment, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-red-400 mt-1">⚠️</span>
                            <span className="text-gray-300">{moment}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {aiInsights.retention_insights.improvement_suggestions.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-indigo-400 mb-2">Improvement Suggestions</h4>
                      <ul className="space-y-2">
                        {aiInsights.retention_insights.improvement_suggestions.map((suggestion, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-indigo-400 mt-1">💡</span>
                            <span className="text-gray-300">{suggestion}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {!loadingAI && !aiInsights && (
                <p className="text-gray-400 text-center py-6">
                  Click "Generate Insights" to get AI-powered retention analysis
                </p>
              )}
            </div>
          </div>
        )}

        {/* Traffic Sources */}
        {trafficSources && trafficSources.traffic_sources.length > 0 && (
          <div className="mb-8">
            <TrafficSourcesChart sources={trafficSources.traffic_sources} />
          </div>
        )}

        {!videoAnalytics.analytics_available && (
          <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-6 text-center">
            <p className="text-yellow-300">
              Analytics data is not available for this video yet. Try syncing analytics from the
              dashboard.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoAnalyticsDetail;
