import React, { useState, useEffect } from 'react';
import { analyzeChannelPatterns, generateScript, generateTitles, type PatternAnalysis, type GeneratedScript, type TitleSuggestion } from '../services/contentStudioApi';

interface ContentStudioProps {
  channelId: number;
  channelName: string;
}

type Tab = 'script' | 'titles' | 'insights';

const ContentStudio: React.FC<ContentStudioProps> = ({ channelId, channelName }) => {
  const [activeTab, setActiveTab] = useState<Tab>('script');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Script Generator State
  const [scriptTopic, setScriptTopic] = useState('');
  const [scriptTone, setScriptTone] = useState('conversational');
  const [scriptMinutes, setScriptMinutes] = useState(8);
  const [scriptFormat, setScriptFormat] = useState('standard');
  const [generatedScript, setGeneratedScript] = useState<GeneratedScript | null>(null);

  // Title Optimizer State
  const [titleTopic, setTitleTopic] = useState('');
  const [generatedTitles, setGeneratedTitles] = useState<TitleSuggestion[]>([]);

  // Insights State
  const [patterns, setPatterns] = useState<PatternAnalysis | null>(null);

  const handleGenerateScript = async () => {
    if (!scriptTopic.trim()) {
      setError('Please enter a video topic');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await generateScript(
        channelId,
        scriptTopic,
        scriptTone,
        scriptMinutes,
        scriptFormat
      );
      setGeneratedScript(result);
    } catch (err: any) {
      setError(err.message || 'Failed to generate script');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateTitles = async () => {
    if (!titleTopic.trim()) {
      setError('Please enter a video topic');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await generateTitles(channelId, titleTopic, 5);
      setGeneratedTitles(result.titles);
    } catch (err: any) {
      setError(err.message || 'Failed to generate titles');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzePatterns = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await analyzeChannelPatterns(channelId, 10);
      setPatterns(result);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze patterns');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'insights' && !patterns) {
      handleAnalyzePatterns();
    }
  }, [activeTab]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">AI Content Studio</h1>
          <p className="text-gray-400">Channel: {channelName}</p>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-700 mb-6">
          <nav className="flex gap-8">
            <button
              onClick={() => setActiveTab('script')}
              className={`pb-4 px-2 font-medium border-b-2 transition-colors ${
                activeTab === 'script'
                  ? 'border-indigo-500 text-indigo-500'
                  : 'border-transparent text-gray-400 hover:text-white'
              }`}
            >
              Script Generator
            </button>
            <button
              onClick={() => setActiveTab('titles')}
              className={`pb-4 px-2 font-medium border-b-2 transition-colors ${
                activeTab === 'titles'
                  ? 'border-indigo-500 text-indigo-500'
                  : 'border-transparent text-gray-400 hover:text-white'
              }`}
            >
              Title Optimizer
            </button>
            <button
              onClick={() => setActiveTab('insights')}
              className={`pb-4 px-2 font-medium border-b-2 transition-colors ${
                activeTab === 'insights'
                  ? 'border-indigo-500 text-indigo-500'
                  : 'border-transparent text-gray-400 hover:text-white'
              }`}
            >
              Performance Insights
            </button>
          </nav>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Script Generator Tab */}
        {activeTab === 'script' && (
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-bold mb-4">Generate AI-Powered Script</h2>
              <p className="text-gray-400 mb-6">
                Using RAG technology, we analyze your top-performing videos to create scripts in your unique style.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Video Topic</label>
                  <input
                    type="text"
                    value={scriptTopic}
                    onChange={(e) => setScriptTopic(e.target.value)}
                    placeholder="e.g., How to increase YouTube watch time"
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Tone</label>
                  <select
                    value={scriptTone}
                    onChange={(e) => setScriptTone(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  >
                    <option value="conversational">Conversational</option>
                    <option value="professional">Professional</option>
                    <option value="educational">Educational</option>
                    <option value="casual">Casual</option>
                    <option value="energetic">Energetic</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Duration (minutes)</label>
                  <input
                    type="number"
                    value={scriptMinutes}
                    onChange={(e) => setScriptMinutes(Number(e.target.value))}
                    min="1"
                    max="30"
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Format</label>
                  <select
                    value={scriptFormat}
                    onChange={(e) => setScriptFormat(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  >
                    <option value="standard">Standard Video</option>
                    <option value="short">YouTube Short</option>
                    <option value="tutorial">Tutorial</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleGenerateScript}
                disabled={loading || !scriptTopic.trim()}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 text-white font-semibold py-3 rounded-lg transition-colors"
              >
                {loading ? 'Generating Script...' : 'Generate Script'}
              </button>
            </div>

            {/* Generated Script Display */}
            {generatedScript && generatedScript.script && (
              <div className="bg-gray-800 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold">Generated Script</h3>
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(generatedScript.script, null, 2))}
                    className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm"
                  >
                    Copy Script
                  </button>
                </div>

                {generatedScript.script.title_suggestion && (
                  <div className="mb-4 p-4 bg-indigo-900/30 rounded-lg">
                    <p className="text-sm text-gray-400 mb-1">Suggested Title</p>
                    <p className="text-lg font-semibold">{generatedScript.script.title_suggestion}</p>
                  </div>
                )}

                <div className="space-y-4">
                  <div className="p-4 bg-gray-700/50 rounded-lg">
                    <p className="text-sm text-indigo-400 font-medium mb-2">HOOK (First 10 seconds)</p>
                    <p className="whitespace-pre-wrap">{generatedScript.script.hook}</p>
                  </div>

                  <div className="p-4 bg-gray-700/50 rounded-lg">
                    <p className="text-sm text-indigo-400 font-medium mb-2">INTRODUCTION</p>
                    <p className="whitespace-pre-wrap">{generatedScript.script.introduction}</p>
                  </div>

                  <div className="p-4 bg-gray-700/50 rounded-lg">
                    <p className="text-sm text-indigo-400 font-medium mb-2">BODY</p>
                    {generatedScript.script.body && generatedScript.script.body.map((section, idx) => (
                      <div key={idx} className="mb-3 last:mb-0">
                        <p className="text-xs text-gray-500 mb-1">[{section.timestamp}]</p>
                        <p className="whitespace-pre-wrap">{section.content}</p>
                      </div>
                    ))}
                  </div>

                  <div className="p-4 bg-gray-700/50 rounded-lg">
                    <p className="text-sm text-indigo-400 font-medium mb-2">CONCLUSION & CTA</p>
                    <p className="whitespace-pre-wrap">{generatedScript.script.conclusion}</p>
                  </div>

                  {generatedScript.script.visual_cues && generatedScript.script.visual_cues.length > 0 && (
                    <div className="p-4 bg-yellow-900/20 rounded-lg">
                      <p className="text-sm text-yellow-400 font-medium mb-2">Visual Cues</p>
                      <ul className="list-disc list-inside space-y-1">
                        {generatedScript.script.visual_cues.map((cue, idx) => (
                          <li key={idx} className="text-sm">{cue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="mt-4 text-xs text-gray-500">
                  Context from {generatedScript.context_used} successful videos used for generation
                </div>
              </div>
            )}
          </div>
        )}

        {/* Title Optimizer Tab */}
        {activeTab === 'titles' && (
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-bold mb-4">Title Optimizer</h2>
              <p className="text-gray-400 mb-6">
                Generate and score title variations based on your channel's successful patterns.
              </p>

              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Video Topic</label>
                <input
                  type="text"
                  value={titleTopic}
                  onChange={(e) => setTitleTopic(e.target.value)}
                  placeholder="e.g., YouTube algorithm tips"
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                />
              </div>

              <button
                onClick={handleGenerateTitles}
                disabled={loading || !titleTopic.trim()}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 text-white font-semibold py-3 rounded-lg transition-colors"
              >
                {loading ? 'Generating Titles...' : 'Generate Title Variations'}
              </button>
            </div>

            {/* Generated Titles Display */}
            {generatedTitles.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-6">
                <h3 className="text-xl font-bold mb-4">Title Suggestions (Ranked by Score)</h3>
                <div className="space-y-4">
                  {generatedTitles.map((titleData, idx) => (
                    <div key={idx} className="p-4 bg-gray-700/50 rounded-lg border-l-4" style={{borderLeftColor: idx === 0 ? '#10b981' : idx === 1 ? '#3b82f6' : '#6b7280'}}>
                      <div className="flex items-start justify-between mb-2">
                        <p className="text-lg font-semibold flex-1">{titleData.title}</p>
                        <button
                          onClick={() => copyToClipboard(titleData.title)}
                          className="ml-4 bg-gray-600 hover:bg-gray-500 px-3 py-1 rounded text-sm"
                        >
                          Copy
                        </button>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-400 mb-2">
                        <span className="font-semibold text-white">Score: {titleData.score}/100 ({titleData.grade})</span>
                        <span>Predicted CTR: {titleData.predicted_ctr}</span>
                      </div>
                      {titleData.factors && titleData.factors.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs text-gray-500 mb-1">Score Factors:</p>
                          <div className="flex flex-wrap gap-2">
                            {titleData.factors.map((factor, fidx) => (
                              <span key={fidx} className={`text-xs px-2 py-1 rounded ${factor.points > 0 ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>
                                {factor.factor} ({factor.points > 0 ? '+' : ''}{factor.points})
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Performance Insights Tab */}
        {activeTab === 'insights' && (
          <div className="space-y-6">
            {loading && !patterns && (
              <div className="text-center py-12">
                <p className="text-gray-400">Analyzing your top videos...</p>
              </div>
            )}

            {patterns && (
              <>
                <div className="bg-gray-800 rounded-lg p-6">
                  <h2 className="text-2xl font-bold mb-4">Performance Patterns</h2>
                  <p className="text-gray-400 mb-6">
                    Analysis of your top {patterns.videos_analyzed} performing videos
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-indigo-900/30 rounded-lg p-4">
                      <p className="text-sm text-gray-400 mb-1">Avg. Views</p>
                      <p className="text-2xl font-bold">{patterns.engagement_patterns.average_views.toLocaleString()}</p>
                    </div>
                    <div className="bg-indigo-900/30 rounded-lg p-4">
                      <p className="text-sm text-gray-400 mb-1">Engagement Rate</p>
                      <p className="text-2xl font-bold">{patterns.engagement_patterns.engagement_rate}%</p>
                    </div>
                    <div className="bg-indigo-900/30 rounded-lg p-4">
                      <p className="text-sm text-gray-400 mb-1">Optimal Duration</p>
                      <p className="text-2xl font-bold">{patterns.duration_patterns.average_minutes} min</p>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-800 rounded-lg p-6">
                  <h3 className="text-xl font-bold mb-4">Top Keywords</h3>
                  <div className="flex flex-wrap gap-2">
                    {patterns.title_patterns.common_keywords.slice(0, 10).map((kw, idx) => (
                      <span key={idx} className="bg-indigo-900/40 px-3 py-1 rounded-full text-sm">
                        {kw.word} ({kw.count})
                      </span>
                    ))}
                  </div>
                </div>

                {patterns.content_themes && patterns.content_themes.length > 0 && (
                  <div className="bg-gray-800 rounded-lg p-6">
                    <h3 className="text-xl font-bold mb-4">Content Themes</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {patterns.content_themes.map((theme, idx) => (
                        <div key={idx} className="bg-gray-700/50 px-4 py-3 rounded-lg">
                          {theme}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="bg-gray-800 rounded-lg p-6">
                  <h3 className="text-xl font-bold mb-4">Recommendations</h3>
                  <ul className="space-y-2">
                    {patterns.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start gap-3">
                        <span className="text-green-400 mt-1">✓</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <button
                  onClick={handleAnalyzePatterns}
                  className="w-full bg-gray-700 hover:bg-gray-600 text-white font-semibold py-3 rounded-lg transition-colors"
                >
                  Refresh Analysis
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ContentStudio;
