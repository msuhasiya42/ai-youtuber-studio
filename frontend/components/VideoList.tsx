import React from 'react';
import type { Video } from '../types';
import VideoCard from './VideoCard';

interface VideoListProps {
  videos: Video[];
  onSeeAll: () => void;
}

const VideoList: React.FC<VideoListProps> = ({ videos, onSeeAll }) => {
  // Show a preview of up to 6 videos
  const previewVideos = videos.slice(0, 6);

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Recent Videos</h2>
        <button
            onClick={onSeeAll}
            className="px-4 py-2 bg-secondary text-text-primary text-sm font-semibold rounded-lg hover:bg-primary transition-colors"
        >
            See All
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {previewVideos.map(video => (
          <VideoCard key={video.id} video={video} />
        ))}
      </div>
    </section>
  );
};

export default VideoList;