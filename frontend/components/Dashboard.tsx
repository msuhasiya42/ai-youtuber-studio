import React, { useState, useCallback, useEffect } from 'react'; // Keep React and hooks, but we'll remove internal fetching
import ChannelHeader from './ChannelHeader';
// import LiveVideos from './LiveVideos'; // Assuming these are child components
// import TopPerformers from './TopPerformers';
// import { getChannel } from '../services/backendApi'; // We'll now pass channelData from App.tsx

interface DashboardProps {
  onDisconnect: () => void;
  onSeeAll: () => void;
  channelData: { // Add channelData prop
    id: number;
    youtube_channel_id: string;
    name: string;
    avatar_url?: string;
    subscribers: number;
    verified: boolean;
  } | null;
  onChannelDataUpdate: (updatedChannel: any) => void; // New prop to handle updates from ChannelHeader
}

const Dashboard: React.FC<DashboardProps> = ({ onDisconnect, onSeeAll, channelData, onChannelDataUpdate }) => { // Destructure new prop
  return (
    <div className="flex flex-col min-h-screen bg-gray-900 text-white p-4">
      <div className="max-w-7xl mx-auto w-full space-y-8">
        {channelData ? (
          <ChannelHeader channel={channelData} onDisconnect={onDisconnect} onRefresh={onChannelDataUpdate} />
        ) : (
          <div className="text-center p-8 text-xl">
            No channel found. Please connect your YouTube channel to get started.
          </div>
        )}
        
        {channelData && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="col-span-full">
                <div className="bg-gray-800 rounded-lg shadow-lg p-6">
                  <h2 className="text-2xl font-semibold mb-4">Dashboard Overview</h2>
                  <p>Welcome to your AI YouTube Studio! Here you'll find insights, video management tools, and script generation capabilities.</p>
                  <p className="mt-2">Connect your YouTube channel to unlock all features.</p>
                  <button 
                    onClick={onSeeAll} 
                    className="mt-4 px-6 py-2 bg-indigo-600 rounded-md hover:bg-indigo-700 transition-colors"
                  >
                    See All Videos (Coming Soon)
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Dashboard;