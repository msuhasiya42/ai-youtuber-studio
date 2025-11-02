import React, { useState, useEffect } from 'react';
import { getVideosWithStatus, retryVideoProcessing } from '../services/backendApi';

interface VideoProcessingDashboardProps {
  channelId: number;
  channelName: string;
}

type FilterType = 'all' | 'processing' | 'complete' | 'error';

interface Video {
  id: number;
  title: string;
  thumbnail_url: string;
  views: number;
  likes: number;
  ctr: number;
  processing_status: string;
  processing_error: string | null;
}

const VideoProcessingDashboard: React.FC<VideoProcessingDashboardProps> = ({ channelId, channelName }) => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>('all');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [retryingVideos, setRetryingVideos] = useState<Set<number>>(new Set());

  const fetchVideos = async () => {
    try {
      const result = await getVideosWithStatus(1, 100);
      setVideos(result.items || []);
      setLastUpdated(new Date());
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch videos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchVideos();

    // Poll every 5 seconds
    const interval = setInterval(() => {
      fetchVideos();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleRetry = async (videoId: number) => {
    setRetryingVideos(prev => new Set(prev).add(videoId));
    try {
      await retryVideoProcessing(videoId);
      // Refresh videos after retry
      await fetchVideos();
    } catch (err: any) {
      setError(err.message || 'Failed to retry video processing');
    } finally {
      setRetryingVideos(prev => {
        const newSet = new Set(prev);
        newSet.delete(videoId);
        return newSet;
      });
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'complete':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'synced':
        return 'bg-gray-500';
      case 'audio_downloading':
      case 'transcribing':
      case 'indexing':
        return 'bg-yellow-500';
      case 'audio_downloaded':
      case 'transcribed':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusLabel = (status: string): string => {
    const labels: { [key: string]: string } = {
      synced: 'Queued',
      audio_downloading: 'Downloading Audio',
      audio_downloaded: 'Audio Ready',
      transcribing: 'Transcribing',
      transcribed: 'Transcribed',
      indexing: 'Indexing',
      complete: 'Complete',
      error: 'Failed',
    };
    return labels[status] || status;
  };

  const isProcessing = (status: string): boolean => {
    return ['audio_downloading', 'transcribing', 'indexing'].includes(status);
  };

  const filteredVideos = videos.filter(video => {
    if (filter === 'all') return true;
    if (filter === 'processing') {
      return isProcessing(video.processing_status) ||
             ['synced', 'audio_downloaded', 'transcribed'].includes(video.processing_status);
    }
    if (filter === 'complete') return video.processing_status === 'complete';
    if (filter === 'error') return video.processing_status === 'error';
    return true;
  });

  const stats = {
    total: videos.length,
    processing: videos.filter(v =>
      isProcessing(v.processing_status) ||
      ['synced', 'audio_downloaded', 'transcribed'].includes(v.processing_status)
    ).length,
    complete: videos.filter(v => v.processing_status === 'complete').length,
    error: videos.filter(v => v.processing_status === 'error').length,
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Video Processing Status</h1>
          <p className="text-gray-400">Channel: {channelName}</p>
          {lastUpdated && (
            <p className="text-sm text-gray-500 mt-1">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-400">Total Videos</div>
            <div className="text-3xl font-bold mt-1">{stats.total}</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-400">Processing</div>
            <div className="text-3xl font-bold mt-1 text-yellow-500">{stats.processing}</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-400">Completed</div>
            <div className="text-3xl font-bold mt-1 text-green-500">{stats.complete}</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-400">Failed</div>
            <div className="text-3xl font-bold mt-1 text-red-500">{stats.error}</div>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-6 flex gap-2">
          {(['all', 'processing', 'complete', 'error'] as FilterType[]).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filter === f
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
            <p className="mt-4 text-gray-400">Loading videos...</p>
          </div>
        )}

        {/* Videos List */}
        {!loading && (
          <div className="space-y-4">
            {filteredVideos.length === 0 ? (
              <div className="bg-gray-800 rounded-lg p-12 text-center">
                <p className="text-gray-400 text-lg">
                  {filter === 'all' ? 'No videos found' : `No ${filter} videos found`}
                </p>
              </div>
            ) : (
              filteredVideos.map(video => (
                <div key={video.id} className="bg-gray-800 rounded-lg p-4 flex items-start gap-4">
                  {/* Thumbnail */}
                  <div className="flex-shrink-0">
                    <img
                      src={video.thumbnail_url}
                      alt={video.title}
                      className="w-32 h-20 object-cover rounded"
                    />
                  </div>

                  {/* Video Info */}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold mb-2 truncate">{video.title}</h3>
                    <div className="flex items-center gap-4 text-sm text-gray-400 mb-2">
                      <span>{video.views?.toLocaleString() || 0} views</span>
                      <span>{video.likes?.toLocaleString() || 0} likes</span>
                    </div>

                    {/* Status Badge */}
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(video.processing_status)} text-white`}>
                        {isProcessing(video.processing_status) && (
                          <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        )}
                        {getStatusLabel(video.processing_status)}
                      </span>
                    </div>

                    {/* Error Message */}
                    {video.processing_error && (
                      <div className="mt-2 text-sm text-red-400 bg-red-900/20 px-3 py-2 rounded">
                        Error: {video.processing_error}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  {video.processing_status === 'error' && (
                    <div className="flex-shrink-0">
                      <button
                        onClick={() => handleRetry(video.id)}
                        disabled={retryingVideos.has(video.id)}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
                      >
                        {retryingVideos.has(video.id) ? 'Retrying...' : 'Retry'}
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoProcessingDashboard;
