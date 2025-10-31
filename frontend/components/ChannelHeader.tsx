
import React, { useState } from 'react';
import type { Channel } from '../types';
import { VerifiedIcon, ViewsIcon, WatchHoursIcon, SubscribersIcon, SettingsIcon, RefreshCwIcon, PlusIcon } from './icons';

interface ChannelHeaderProps {
  channel: Channel;
  onDisconnect: () => void;
  onRefresh: (updatedChannel: Channel) => void; // New prop to notify parent of refresh
}

const ChannelHeader: React.FC<ChannelHeaderProps> = ({ channel, onDisconnect, onRefresh }) => {
  const [filter, setFilter] = useState('All time');
  const [isRefreshing, setIsRefreshing] = useState(false); // State for refresh button loading

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  console.log("channel", channel);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const { refreshChannelData } = await import('../services/backendApi'); // Dynamic import to avoid circular dependency if needed
      const updatedChannel = await refreshChannelData(channel.id);
      onRefresh(updatedChannel); // Notify parent with updated data
    } catch (error) {
      console.error('Failed to refresh channel data:', error);
      alert(`Failed to refresh data: ${error.message}`);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <header className="bg-surface rounded-xl p-4 sm:p-6 shadow-lg">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <img src={channel.avatar_url} alt={channel.name} className="w-16 h-16 sm:w-20 sm:h-20 rounded-full border-2 border-primary" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold text-text-primary">{channel.name}</h1>
              {channel.verified && <VerifiedIcon className="w-5 h-5 text-primary" />}
            </div>
            <div className="flex items-center gap-2 text-text-secondary mt-1">
                <SubscribersIcon className="w-4 h-4"/>
                <span className="font-semibold">{formatNumber(channel.subscribers)}</span>
                <span>subscribers</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
             <button title="Generate Ideas" className="p-2 bg-secondary hover:bg-primary-hover rounded-lg transition-colors"><PlusIcon className="w-5 h-5"/></button>
             <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                title="Refresh Channel Data"
                className="p-2 bg-secondary hover:bg-primary-hover rounded-lg transition-colors"
             >
                {isRefreshing ? (
                    <svg className="animate-spin h-5 w-5 text-text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                ) : (
                    <RefreshCwIcon className="w-5 h-5"/>
                )}
             </button>
             <button onClick={onDisconnect} title="Settings & Disconnect" className="p-2 bg-secondary hover:bg-primary-hover rounded-lg transition-colors"><SettingsIcon className="w-5 h-5"/></button>
        </div>
      </div>
      
      <div className="mt-6 border-t border-border pt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="flex flex-col gap-2 p-4 bg-background rounded-lg">
          <div className="flex items-center gap-2 text-text-secondary text-sm">
            <ViewsIcon className="w-4 h-4" />
            <span>Total Views</span>
          </div>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(channel.totalViews)}</p>
        </div>
        <div className="flex flex-col gap-2 p-4 bg-background rounded-lg">
          <div className="flex items-center gap-2 text-text-secondary text-sm">
            <WatchHoursIcon className="w-4 h-4" />
            <span>Total Watch Hours</span>
          </div>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(channel.totalWatchHours)}</p>
        </div>
        <div className="col-span-2 md:col-span-2 flex items-center justify-end">
            <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-secondary border border-border text-text-primary text-sm rounded-lg focus:ring-primary focus:border-primary block w-full sm:w-auto p-2.5"
                >
                <option>All time</option>
                <option>Last 3 months</option>
                <option>Last 1 month</option>
                <option>Last 1 week</option>
            </select>
        </div>
      </div>
    </header>
  );
};

export default ChannelHeader;