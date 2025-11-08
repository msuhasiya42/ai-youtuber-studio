import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { RetentionCurve } from '../services/analyticsApi';

interface RetentionCurveChartProps {
  data: RetentionCurve;
  height?: number;
}

const RetentionCurveChart: React.FC<RetentionCurveChartProps> = ({ data, height = 400 }) => {
  // Transform retention points for recharts
  const chartData = data.retention_points.map((point) => ({
    time: Math.floor(point.elapsed_seconds / 60), // Convert to minutes
    timeSeconds: point.elapsed_seconds,
    retention: point.retention_percentage,
  }));

  // Format time for tooltip
  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
          <p className="text-sm text-gray-300">
            Time: {formatTime(payload[0].payload.timeSeconds)}
          </p>
          <p className="text-sm font-semibold text-indigo-400">
            Retention: {payload[0].value.toFixed(1)}%
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="mb-4">
        <h3 className="text-xl font-bold mb-2">Audience Retention Curve</h3>
        <p className="text-sm text-gray-400">{data.title}</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <div className="bg-gray-700/50 rounded p-3">
          <p className="text-xs text-gray-400 mb-1">10s</p>
          <p className="text-lg font-bold text-green-400">
            {data.retention_at_10s?.toFixed(1) || 'N/A'}%
          </p>
        </div>
        <div className="bg-gray-700/50 rounded p-3">
          <p className="text-xs text-gray-400 mb-1">30s</p>
          <p className="text-lg font-bold text-blue-400">
            {data.retention_at_30s?.toFixed(1) || 'N/A'}%
          </p>
        </div>
        <div className="bg-gray-700/50 rounded p-3">
          <p className="text-xs text-gray-400 mb-1">60s</p>
          <p className="text-lg font-bold text-purple-400">
            {data.retention_at_60s?.toFixed(1) || 'N/A'}%
          </p>
        </div>
        <div className="bg-gray-700/50 rounded p-3">
          <p className="text-xs text-gray-400 mb-1">Halfway</p>
          <p className="text-lg font-bold text-yellow-400">
            {data.retention_at_halfway?.toFixed(1) || 'N/A'}%
          </p>
        </div>
        <div className="bg-gray-700/50 rounded p-3">
          <p className="text-xs text-gray-400 mb-1">End</p>
          <p className="text-lg font-bold text-red-400">
            {data.retention_at_end?.toFixed(1) || 'N/A'}%
          </p>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="time"
            stroke="#9CA3AF"
            label={{ value: 'Time (minutes)', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            stroke="#9CA3AF"
            label={{ value: 'Retention (%)', angle: -90, position: 'insideLeft' }}
            domain={[0, 100]}
          />
          <Tooltip content={<CustomTooltip />} />
          {data.critical_drop_point_seconds && (
            <ReferenceLine
              x={Math.floor(data.critical_drop_point_seconds / 60)}
              stroke="#EF4444"
              strokeDasharray="3 3"
              label={{
                value: 'Critical Drop',
                position: 'top',
                fill: '#EF4444',
                fontSize: 12,
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="retention"
            stroke="#6366F1"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Additional Info */}
      {data.critical_drop_point_seconds && (
        <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded">
          <p className="text-sm text-red-300">
            <span className="font-semibold">Critical drop point:</span>{' '}
            {formatTime(data.critical_drop_point_seconds)} - Consider reviewing content at this
            timestamp
          </p>
        </div>
      )}
    </div>
  );
};

export default RetentionCurveChart;
