
import React, { useState, useEffect, useCallback } from 'react';
import type { Video, AIGeneratedContent } from '../types';
import { generateIdeasAndScript } from '../services/geminiService';
import { XIcon, SparklesIcon, FileTextIcon, LightbulbIcon, CopyIcon, CheckIcon } from './icons';

interface ScriptStudioModalProps {
  video: Video;
  onClose: () => void;
}

const ScriptStudioModal: React.FC<ScriptStudioModalProps> = ({ video, onClose }) => {
  const [content, setContent] = useState<AIGeneratedContent | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'ideas' | 'script'>('ideas');
  const [copied, setCopied] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await generateIdeasAndScript(video.title);
      setContent(result);
    } catch (e) {
      setError('Failed to generate AI content. Please try again.');
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, [video.title]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderContent = () => {
    if (isLoading) {
      return (
         <div className="flex flex-col items-center justify-center p-8 h-64">
            <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
            <p className="text-text-secondary">Generating ideas and script...</p>
         </div>
      );
    }
    if (error) {
      return <div className="text-red-400 p-8 text-center">{error}</div>;
    }
    if (content) {
      return (
        <div className="p-4 sm:p-6">
            <div className="flex border-b border-border mb-4">
                <button onClick={() => setActiveTab('ideas')} className={`px-4 py-2 text-sm font-medium ${activeTab === 'ideas' ? 'text-primary border-b-2 border-primary' : 'text-text-secondary'}`}>
                    <LightbulbIcon className="inline w-4 h-4 mr-1"/> Ideas
                </button>
                <button onClick={() => setActiveTab('script')} className={`px-4 py-2 text-sm font-medium ${activeTab === 'script' ? 'text-primary border-b-2 border-primary' : 'text-text-secondary'}`}>
                    <FileTextIcon className="inline w-4 h-4 mr-1"/> Script
                </button>
            </div>
            
            {activeTab === 'ideas' && (
                <div className="space-y-3">
                    {content.ideas.map((idea, index) => (
                        <div key={index} className="bg-background p-3 rounded-lg text-text-secondary">{idea}</div>
                    ))}
                </div>
            )}
            {activeTab === 'script' && (
                <div className="relative">
                    <button onClick={() => handleCopy(content.script)} className="absolute top-2 right-2 p-2 bg-secondary rounded-lg hover:bg-primary-hover transition-colors">
                        {copied ? <CheckIcon className="w-4 h-4 text-green-400"/> : <CopyIcon className="w-4 h-4"/>}
                    </button>
                    <pre className="whitespace-pre-wrap bg-background p-4 rounded-lg text-text-secondary font-sans text-sm h-[50vh] overflow-y-auto">{content.script}</pre>
                </div>
            )}
        </div>
      );
    }
    return null;
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-surface rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        <header className="flex items-center justify-between p-4 border-b border-border sticky top-0 bg-surface">
          <h2 className="flex items-center gap-2 text-lg font-bold"><SparklesIcon className="w-6 h-6 text-primary" /> AI Script Studio</h2>
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

export default ScriptStudioModal;
