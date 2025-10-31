
import React, { useState } from 'react';
import type { Channel } from '../types';
import { VerifiedIcon, ViewsIcon, WatchHoursIcon, SubscribersIcon, SettingsIcon, RefreshCwIcon, PlusIcon } from './icons';

interface ChannelHeaderProps {
  channel: Channel;
  onDisconnect: () => void;
}

const ChannelHeader: React.FC<ChannelHeaderProps> = ({ channel, onDisconnect }) => {
  const [filter, setFilter] = useState('All time');

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <header className="bg-surface rounded-xl p-4 sm:p-6 shadow-lg">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <img src={channel.avatarUrl} alt={channel.name} className="w-16 h-16 sm:w-20 sm:h-20 rounded-full border-2 border-primary" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold text-text-primary">{channel.name}</h1>
              {channel.isVerified && <VerifiedIcon className="w-5 h-5 text-primary" />}
            </div>
            <div className="flex items-center gap-2 text-text-secondary mt-1">
                <SubscribersIcon className="w-4 h-4"/>
                <span className="font-semibold">{formatNumber(channel.subscriberCount)}</span>
                <span>subscribers</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
             <button title="Generate Ideas" className="p-2 bg-secondary hover:bg-primary-hover rounded-lg transition-colors"><PlusIcon className="w-5 h-5"/></button>
             <button title="Ingest New Videos" className="p-2 bg-secondary hover:bg-primary-hover rounded-lg transition-colors"><RefreshCwIcon className="w-5 h-5"/></button>
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
