
import React, { useState, useEffect } from 'react';
import type { Video } from '../types';
import VideoCard from './VideoCard';

interface LiveVideosProps {
  videos: Video[];
}

const LiveVideos: React.FC<LiveVideosProps> = ({ videos }) => {
  const [liveVideos, setLiveVideos] = useState(videos);

  useEffect(() => {
    const interval = setInterval(() => {
      setLiveVideos(currentVideos => 
        currentVideos.map(video => ({
          ...video,
          viewCount: video.viewCount + Math.floor(Math.random() * 20),
          likeCount: video.likeCount + Math.floor(Math.random() * 5),
        }))
      );
    }, 3000); // Poll every 3 seconds to simulate live updates

    return () => clearInterval(interval);
  }, []);

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-2xl font-bold">Live Quick View</h2>
        <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
        </span>
      </div>
      <div className="flex sm:grid sm:grid-cols-2 lg:grid-cols-3 gap-6 overflow-x-auto sm:overflow-visible pb-4 sm:pb-0 snap-x snap-mandatory">
        {liveVideos.map(video => (
          <div key={video.id} className="snap-start flex-shrink-0 w-[80vw] sm:w-auto">
            <VideoCard video={video} isLive={true} />
          </div>
        ))}
      </div>
    </section>
  );
};

export default LiveVideos;
