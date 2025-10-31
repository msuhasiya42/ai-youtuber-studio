import React, { useEffect, useState } from 'react';
import ChannelHeader from './ChannelHeader';
import LiveVideos from './LiveVideos';
import TopPerformers from './TopPerformers';
import VideoList from './VideoList';
import { getChannel } from '../services/backendApi';
import type { Channel, Video } from '../types';

interface DashboardProps {
  onDisconnect: () => void;
  onSeeAll: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onDisconnect, onSeeAll }) => {
  const [channel, setChannel] = useState<Channel|null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);

  useEffect(() => {
    setLoading(true);
    getChannel().then((data) => {
      if (!data.channel) throw new Error('No channel found.');
      // Map API shape to Channel and Video types
      setChannel({
        id: data.channel.id,
        name: data.channel.name,
        avatarUrl: data.channel.avatar_url,
        isVerified: data.channel.verified,
        subscriberCount: data.channel.subscribers,
        totalViews: 0, // Placeholder, backend should return this!
        totalWatchHours: 0, // Placeholder, backend should return this!
      });
      // Videos for dashboard: combine top_videos and add additional if backend supports
      setVideos(data.top_videos.map((v:any) => ({
        id: String(v.id),
        title: v.title,
        thumbnailUrl: v.thumbnail_url,
        publishedAt: '',
        duration: '',
        viewCount: v.views,
        likeCount: v.likes,
        commentCount: 0,
        ctr: v.ctr,
      })));
      setError(null);
    }).catch((e) => {
      setError(e.message || 'Failed loading channel');
      setChannel(null);
      setVideos([]);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="w-full min-h-[30vh] flex items-center justify-center text-lg font-bold">Loading…</div>;
  if (error) return <div className="w-full min-h-[30vh] text-center text-red-500 font-bold">{error}</div>;
  if (!channel) return <div className="w-full min-h-[30vh] text-center text-gray-500">No channel data found.</div>;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-2xl mx-auto">
      <div className="sticky top-0 z-10 bg-background pt-4 -mt-4 sm:static sm:pt-0 sm:mt-0">
         <ChannelHeader channel={channel} onDisconnect={onDisconnect} />
      </div>
      <main className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-3">
          <LiveVideos videos={videos.slice(0, 3)} />
        </div>
        <div className="lg:col-span-2">
           <VideoList videos={videos.slice(3)} onSeeAll={onSeeAll} />
        </div>
        <div className="lg:col-span-1">
          <TopPerformers videos={videos} />
        </div>
      </main>
    </div>
  );
};

export default Dashboard;