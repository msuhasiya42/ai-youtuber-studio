import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend,
} from 'recharts';
import type { TrafficSource } from '../services/analyticsApi';

interface TrafficSourcesChartProps {
  sources: TrafficSource[];
  title?: string;
  chartType?: 'bar' | 'pie';
  height?: number;
}

const COLORS = ['#6366F1', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#3B82F6', '#EF4444'];

const TrafficSourcesChart: React.FC<TrafficSourcesChartProps> = ({
  sources,
  title = 'Traffic Sources',
  chartType = 'bar',
  height = 400,
}) => {
  // Sort sources by views descending
  const sortedSources = [...sources].sort((a, b) => b.views - a.views);

  // Format source type for display
  const formatSourceType = (type: string) => {
    return type
      .replace('YT_', 'YouTube ')
      .replace('_', ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  // Prepare data for charts
  const chartData = sortedSources.map((source) => ({
    name: formatSourceType(source.source_type),
    views: source.views,
    percentage: source.percentage_of_views,
    watchTime: source.watch_time_minutes,
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
          <p className="text-sm font-semibold text-white mb-2">{payload[0].payload.name}</p>
          <p className="text-sm text-gray-300">
            Views: {payload[0].payload.views.toLocaleString()}
          </p>
          <p className="text-sm text-gray-300">
            Percentage: {payload[0].payload.percentage.toFixed(1)}%
          </p>
          <p className="text-sm text-gray-300">
            Watch Time: {payload[0].payload.watchTime.toLocaleString()} min
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h3 className="text-xl font-bold mb-4">{title}</h3>

      {/* Source Breakdown Table */}
      <div className="mb-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="text-left py-2 px-3 text-gray-400 font-medium">Source</th>
              <th className="text-right py-2 px-3 text-gray-400 font-medium">Views</th>
              <th className="text-right py-2 px-3 text-gray-400 font-medium">%</th>
              <th className="text-right py-2 px-3 text-gray-400 font-medium">Watch Time</th>
            </tr>
          </thead>
          <tbody>
            {sortedSources.map((source, idx) => (
              <tr key={idx} className="border-b border-gray-700/50">
                <td className="py-2 px-3">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                    />
                    <span>{formatSourceType(source.source_type)}</span>
                  </div>
                </td>
                <td className="text-right py-2 px-3 font-mono">
                  {source.views.toLocaleString()}
                </td>
                <td className="text-right py-2 px-3 font-mono">
                  {source.percentage_of_views.toFixed(1)}%
                </td>
                <td className="text-right py-2 px-3 font-mono text-gray-400">
                  {source.watch_time_minutes.toLocaleString()} min
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Chart */}
      {chartType === 'bar' ? (
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 80 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="name"
              stroke="#9CA3AF"
              angle={-45}
              textAnchor="end"
              height={100}
              interval={0}
            />
            <YAxis stroke="#9CA3AF" label={{ value: 'Views', angle: -90, position: 'insideLeft' }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="views" radius={[8, 8, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percentage }) => `${name}: ${percentage.toFixed(1)}%`}
              outerRadius={120}
              fill="#8884d8"
              dataKey="views"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}

      {/* Top Source Highlight */}
      {sortedSources.length > 0 && (
        <div className="mt-4 p-3 bg-indigo-900/20 border border-indigo-500/30 rounded">
          <p className="text-sm text-indigo-300">
            <span className="font-semibold">Top traffic source:</span>{' '}
            {formatSourceType(sortedSources[0].source_type)} (
            {sortedSources[0].percentage_of_views.toFixed(1)}% of views)
          </p>
        </div>
      )}
    </div>
  );
};

export default TrafficSourcesChart;
