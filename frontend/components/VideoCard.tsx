
import React, { useState } from 'react';
import type { Video } from '../types';
import { ViewsIcon, ThumbsUpIcon, SparklesIcon } from './icons';
import ScriptStudioModal from './ScriptStudioModal';


interface VideoCardProps {
  video: Video;
  isLive?: boolean;
}

const VideoCard: React.FC<VideoCardProps> = ({ video, isLive = false }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };
  
  const timeSince = (dateString: string) => {
    const date = new Date(dateString);
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " minutes ago";
    return Math.floor(seconds) + " seconds ago";
  }

  return (
    <>
      <div className="bg-surface rounded-xl overflow-hidden shadow-lg transition-all duration-300 hover:shadow-primary/20 hover:ring-2 hover:ring-primary">
        <div className="relative">
          <img src={video.thumbnailUrl} alt={video.title} className="w-full h-48 object-cover" />
          <span className="absolute bottom-2 right-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">{video.duration}</span>
           {isLive && (
             <span className="absolute top-2 left-2 bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full animate-pulse-fast">LIVE</span>
           )}
        </div>
        <div className="p-4">
          <h3 className="font-bold text-md text-text-primary h-12 overflow-hidden">{video.title}</h3>
          <p className="text-sm text-text-secondary mt-1">{timeSince(video.publishedAt)}</p>
          
          <div className="flex items-center justify-between mt-4 text-sm">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5 text-text-secondary">
                <ViewsIcon className="w-4 h-4" /> {formatNumber(video.viewCount)}
              </span>
              <span className="flex items-center gap-1.5 text-text-secondary">
                <ThumbsUpIcon className="w-4 h-4" /> {formatNumber(video.likeCount)}
              </span>
            </div>
            <button 
                onClick={() => setIsModalOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-secondary text-text-primary rounded-md text-xs font-semibold hover:bg-primary transition-colors">
                <SparklesIcon className="w-4 h-4" />
                <span>AI Studio</span>
            </button>
          </div>
        </div>
      </div>
      {isModalOpen && <ScriptStudioModal video={video} onClose={() => setIsModalOpen(false)} />}
    </>
  );
};

export default VideoCard;
