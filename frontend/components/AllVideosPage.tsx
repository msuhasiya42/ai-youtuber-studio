import React, { useState } from 'react';
import type { Video } from '../types';
import VideoCard from './VideoCard';
import { ArrowLeftIcon } from './icons';
import { videos as allVideos } from '../services/mockData';

interface AllVideosPageProps {
  onBack: () => void;
}

const VIDEOS_PER_PAGE = 8;

const AllVideosPage: React.FC<AllVideosPageProps> = ({ onBack }) => {
  const [visibleCount, setVisibleCount] = useState(VIDEOS_PER_PAGE);

  const handleLoadMore = () => {
    setVisibleCount(prevCount => prevCount + VIDEOS_PER_PAGE);
  };

  const hasMore = visibleCount < allVideos.length;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-2xl mx-auto">
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 rounded-full hover:bg-surface transition-colors" aria-label="Back to Dashboard">
            <ArrowLeftIcon className="w-6 h-6" />
          </button>
          <h1 className="text-3xl font-bold">All Videos</h1>
        </div>
      </header>
      <main>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
          {allVideos.slice(0, visibleCount).map(video => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
        {hasMore && (
          <div className="mt-8 text-center">
            <button
              onClick={handleLoadMore}
              className="px-6 py-3 bg-primary text-white font-semibold rounded-lg shadow-md hover:bg-primary-hover transition-colors"
            >
              Load More
            </button>
          </div>
        )}
      </main>
    </div>
  );
};

export default AllVideosPage;