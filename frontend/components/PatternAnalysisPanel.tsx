import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  getDurationAnalysis,
  getHookAnalysis,
  getPostingTimeAnalysis,
  getEngagementAnalysis,
  type DurationAnalysis,
  type HookAnalysis,
  type PostingTimeAnalysis,
  type EngagementAnalysis,
} from '../services/analyticsApi';

interface PatternAnalysisPanelProps {
  channelId: number;
}

const COLORS = ['#6366F1', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981'];

const PatternAnalysisPanel: React.FC<PatternAnalysisPanelProps> = ({ channelId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'duration' | 'hooks' | 'timing' | 'engagement'>(
    'duration'
  );

  const [durationData, setDurationData] = useState<DurationAnalysis | null>(null);
  const [hookData, setHookData] = useState<HookAnalysis | null>(null);
  const [timingData, setTimingData] = useState<PostingTimeAnalysis | null>(null);
  const [engagementData, setEngagementData] = useState<EngagementAnalysis | null>(null);

  useEffect(() => {
    loadData();
  }, [channelId]);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [duration, hooks, timing, engagement] = await Promise.all([
        getDurationAnalysis(channelId),
        getHookAnalysis(channelId),
        getPostingTimeAnalysis(channelId),
        getEngagementAnalysis(channelId),
      ]);

      setDurationData(duration);
      setHookData(hooks);
      setTimingData(timing);
      setEngagementData(engagement);
    } catch (err: any) {
      setError(err.message || 'Failed to load pattern analysis');
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'duration', label: 'Video Duration', icon: '⏱️' },
    { id: 'hooks', label: 'Hook Strength', icon: '🎣' },
    { id: 'timing', label: 'Posting Time', icon: '📅' },
    { id: 'engagement', label: 'Engagement', icon: '💬' },
  ] as const;

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <p className="text-gray-400 text-center">Loading pattern analysis...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <p className="text-red-400 text-center">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-2xl font-bold mb-6">Pattern Analysis</h2>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Duration Analysis */}
      {activeTab === 'duration' && durationData && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-1">Optimal Duration</p>
              <p className="text-2xl font-bold text-indigo-400">
                {durationData.optimal_duration_range}
              </p>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-1">Correlation Strength</p>
              <p className="text-2xl font-bold text-purple-400">
                {Math.abs(durationData.correlation_coefficient).toFixed(2)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {durationData.correlation_coefficient > 0 ? 'Positive' : 'Negative'} correlation
              </p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={durationData.duration_buckets}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="range" stroke="#9CA3AF" />
              <YAxis
                stroke="#9CA3AF"
                label={{ value: 'Avg Retention %', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '0.5rem',
                }}
              />
              <Bar dataKey="avg_retention" radius={[8, 8, 0, 0]}>
                {durationData.duration_buckets.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Hook Analysis */}
      {activeTab === 'hooks' && hookData && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-1">Avg Hook Strength</p>
              <p className="text-2xl font-bold text-green-400">
                {hookData.avg_hook_strength.toFixed(1)}%
              </p>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-1">Strong Hooks</p>
              <p className="text-2xl font-bold text-blue-400">{hookData.strong_hooks_count}</p>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-1">Weak Hooks</p>
              <p className="text-2xl font-bold text-red-400">{hookData.weak_hooks_count}</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={hookData.hook_performance_buckets}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="range" stroke="#9CA3AF" />
              <YAxis
                stroke="#9CA3AF"
                label={{ value: 'Avg Views', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '0.5rem',
                }}
              />
              <Bar dataKey="avg_views" fill="#10B981" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>

          {hookData.recommendations.length > 0 && (
            <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
              <h4 className="font-semibold mb-2 text-green-300">Recommendations</h4>
              <ul className="space-y-1">
                {hookData.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                    <span className="text-green-400 mt-0.5">✓</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Timing Analysis */}
      {activeTab === 'timing' && timingData && (
        <div className="space-y-4">
          <div className="bg-gray-700/50 rounded-lg p-4 mb-6">
            <p className="text-sm text-gray-400 mb-1">Best Day to Post</p>
            <p className="text-2xl font-bold text-indigo-400">{timingData.best_day}</p>
          </div>

          <h4 className="font-semibold mb-3">Performance by Day of Week</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={timingData.day_of_week_performance}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="day" stroke="#9CA3AF" />
              <YAxis
                stroke="#9CA3AF"
                label={{ value: 'Avg Views', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '0.5rem',
                }}
              />
              <Bar dataKey="avg_views" radius={[8, 8, 0, 0]}>
                {timingData.day_of_week_performance.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {timingData.recommendations.length > 0 && (
            <div className="bg-indigo-900/20 border border-indigo-500/30 rounded-lg p-4">
              <h4 className="font-semibold mb-2 text-indigo-300">Recommendations</h4>
              <ul className="space-y-1">
                {timingData.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                    <span className="text-indigo-400 mt-0.5">✓</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Engagement Analysis */}
      {activeTab === 'engagement' && engagementData && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-1">Engagement Rate</p>
              <p className="text-2xl font-bold text-indigo-400">
                {engagementData.avg_engagement_rate.toFixed(2)}%
              </p>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-1">Like Rate</p>
              <p className="text-2xl font-bold text-green-400">
                {engagementData.like_rate.toFixed(2)}%
              </p>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-1">Comment Rate</p>
              <p className="text-2xl font-bold text-blue-400">
                {engagementData.comment_rate.toFixed(2)}%
              </p>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-1">Share Rate</p>
              <p className="text-2xl font-bold text-purple-400">
                {engagementData.share_rate.toFixed(2)}%
              </p>
            </div>
          </div>

          {engagementData.engagement_drivers.length > 0 && (
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 mb-4">
              <h4 className="font-semibold mb-2 text-blue-300">Engagement Drivers</h4>
              <div className="flex flex-wrap gap-2">
                {engagementData.engagement_drivers.map((driver, idx) => (
                  <span
                    key={idx}
                    className="bg-blue-900/40 px-3 py-1 rounded-full text-sm text-blue-200"
                  >
                    {driver}
                  </span>
                ))}
              </div>
            </div>
          )}

          {engagementData.recommendations.length > 0 && (
            <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
              <h4 className="font-semibold mb-2 text-purple-300">Recommendations</h4>
              <ul className="space-y-1">
                {engagementData.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                    <span className="text-purple-400 mt-0.5">✓</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PatternAnalysisPanel;
