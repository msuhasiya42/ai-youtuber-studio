
import React, { useState, useMemo } from 'react';
import type { Video } from '../types';
import InsightModal from './InsightModal';
import { EyeIcon } from './icons';

interface TopPerformersProps {
  videos: Video[];
}

const TopPerformers: React.FC<TopPerformersProps> = ({ videos }) => {
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);

  const topVideos = useMemo(() => {
    return [...videos]
      .sort((a, b) => b.viewCount - a.viewCount)
      .slice(0, 5);
  }, [videos]);

  const handleViewInsights = (video: Video) => {
    setSelectedVideo(video);
  };
  
  const handleCloseModal = () => {
    setSelectedVideo(null);
  };
  
  const formatNumber = (num: number) => {
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <>
      <section className="bg-surface rounded-xl p-6 shadow-lg">
        <h2 className="text-2xl font-bold mb-4">Top Performers</h2>
        <div className="space-y-4">
          {topVideos.map((video, index) => (
            <div key={video.id} className="flex items-center gap-4 p-2 rounded-lg hover:bg-background transition-colors">
              <span className="font-bold text-lg text-text-secondary">{index + 1}</span>
              <img src={video.thumbnailUrl} alt={video.title} className="w-20 h-12 object-cover rounded-md" />
              <div className="flex-1">
                <h4 className="text-sm font-semibold truncate">{video.title}</h4>
                <p className="text-xs text-text-secondary">{formatNumber(video.viewCount)} views</p>
              </div>
              <button
                onClick={() => handleViewInsights(video)}
                className="p-2 text-text-secondary hover:text-primary transition-colors"
                title="View AI Insights"
              >
                <EyeIcon className="w-5 h-5" />
              </button>
            </div>
          ))}
        </div>
      </section>
      {selectedVideo && <InsightModal video={selectedVideo} onClose={handleCloseModal} />}
    </>
  );
};

export default TopPerformers;
