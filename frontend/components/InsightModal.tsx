
import React, { useState, useEffect } from 'react';
import type { Video, AIInsight } from '../types';
import { generateInsights } from '../services/geminiService';
import { XIcon, LightbulbIcon, ChevronsRightIcon, TestTubeIcon, FileTextIcon } from './icons';

interface InsightModalProps {
  video: Video;
  onClose: () => void;
}

const InsightModal: React.FC<InsightModalProps> = ({ video, onClose }) => {
  const [insight, setInsight] = useState<AIInsight | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await generateInsights(video.title);
        setInsight(result);
      } catch (e) {
        setError('Failed to generate AI insights. Please try again.');
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchInsights();
  }, [video.title]);

  const renderContent = () => {
    if (isLoading) {
      return (
         <div className="flex flex-col items-center justify-center p-8">
            <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
            <p className="text-text-secondary">Generating deep insights for "{video.title}"...</p>
         </div>
      );
    }
    if (error) {
      return <div className="text-red-400 p-8 text-center">{error}</div>;
    }
    if (insight) {
      return (
        <div className="p-6 space-y-6">
          <InsightSection title="Summary" icon={<FileTextIcon className="w-5 h-5" />} content={[insight.summary]}/>
          <InsightSection title="Key Drivers" icon={<ChevronsRightIcon className="w-5 h-5" />} content={insight.keyDrivers} />
          <InsightSection title="Replicable Patterns" icon={<LightbulbIcon className="w-5 h-5" />} content={insight.replicablePatterns} />
          <InsightSection title="Suggested Experiments" icon={<TestTubeIcon className="w-5 h-5" />} content={insight.suggestedExperiments} />
        </div>
      );
    }
    return null;
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-surface rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <header className="flex items-center justify-between p-4 border-b border-border sticky top-0 bg-surface">
          <h2 className="text-lg font-bold">AI Insights: <span className="text-primary">{video.title}</span></h2>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-secondary">
            <XIcon className="w-6 h-6" />
          </button>
        </header>
        <div className="overflow-y-auto">
            {renderContent()}
        </div>
      </div>
    </div>
  );
};

interface InsightSectionProps {
    title: string;
    icon: React.ReactNode;
    content: string[];
}

const InsightSection: React.FC<InsightSectionProps> = ({ title, icon, content }) => (
    <div>
        <h3 className="flex items-center gap-2 text-lg font-semibold text-primary mb-2">
            {icon}
            {title}
        </h3>
        {content.length > 1 ? (
             <ul className="list-disc list-inside space-y-1 text-text-secondary pl-2">
                {content.map((item, index) => <li key={index}>{item}</li>)}
            </ul>
        ) : (
            <p className="text-text-secondary">{content[0]}</p>
        )}
    </div>
);


export default InsightModal;
