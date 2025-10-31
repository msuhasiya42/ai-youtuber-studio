
export interface Channel {
  id: string;
  name: string;
  avatarUrl: string;
  isVerified: boolean;
  subscriberCount: number;
  totalViews: number;
  totalWatchHours: number;
}

export interface Video {
  id: string;
  title: string;
  thumbnailUrl: string;
  publishedAt: string;
  duration: string;
  viewCount: number;
  likeCount: number;
  commentCount: number;
  ctr?: number; // Click-through rate
}

export interface AIGeneratedContent {
  summary: string;
  ideas: string[];
  script: string;
}

export interface AIInsight {
  summary: string;
  keyDrivers: string[];
  replicablePatterns: string[];
  suggestedExperiments: string[];
}
