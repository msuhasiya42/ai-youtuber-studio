
import { GoogleGenAI, Type } from "@google/genai";
import type { AIInsight, AIGeneratedContent } from '../types';

const API_KEY = process.env.GEMINI_API_KEY;

if (!API_KEY) {
  throw new Error("API_KEY environment variable is not set");
}

const ai = new GoogleGenAI({ apiKey: API_KEY });

const model = 'gemini-2.5-flash';

export const generateInsights = async (videoTitle: string): Promise<AIInsight> => {
  const prompt = `
    As a YouTube growth expert, analyze the potential reasons for the success of a video titled "${videoTitle}". 
    Provide a structured insight report. The video is one of the top-performing ones on its channel.
    Your analysis should be based on common YouTube success factors like title, topic relevance, potential hook, and thumbnail appeal.
    Format the response as a JSON object with the following keys: "summary", "keyDrivers", "replicablePatterns", "suggestedExperiments".
    - summary: A brief paragraph explaining the likely appeal of the video.
    - keyDrivers: A bulleted list (array of strings) of 3-4 key factors that likely contributed to its success (e.g., "Catchy & Mysterious Title", "Addresses a high-demand topic").
    - replicablePatterns: A bulleted list (array of strings) of 2-3 patterns from this video that the creator could apply to future content.
    - suggestedExperiments: A bulleted list (array of strings) of 2 A/B test ideas for future videos, inspired by this one (e.g., "Test a question-based title vs. a statement").
  `;

  try {
    const response = await ai.models.generateContent({
        model,
        contents: prompt,
        config: {
            responseMimeType: "application/json",
            responseSchema: {
                type: Type.OBJECT,
                properties: {
                    summary: { type: Type.STRING },
                    keyDrivers: { type: Type.ARRAY, items: { type: Type.STRING } },
                    replicablePatterns: { type: Type.ARRAY, items: { type: Type.STRING } },
                    suggestedExperiments: { type: Type.ARRAY, items: { type: Type.STRING } }
                }
            }
        }
    });

    const jsonText = response.text.trim();
    const parsed = JSON.parse(jsonText);
    return parsed as AIInsight;
  } catch (error) {
    console.error("Error generating insights:", error);
    throw new Error("Failed to communicate with the Gemini API.");
  }
};

export const generateIdeasAndScript = async (videoTitle: string): Promise<AIGeneratedContent> => {
    const prompt = `
        You are an AI assistant for a YouTuber. The creator just made a successful video titled "${videoTitle}".
        Your task is to generate new content ideas and a sample script based on this video.
        
        Format the response as a single JSON object with the following keys: "summary", "ideas", "script".
        - summary: A one-sentence summary of the original video topic.
        - ideas: An array of 3 new, distinct video ideas that are related to or inspired by the original video. Each idea should be a string.
        - script: A short, sample YouTube video script for the *first* new video idea. The script should be a single string and include an engaging hook, a main body with a few key points, and a call-to-action (CTA) at the end. Use markdown-style formatting like "[SCENE START]" or "HOST:" for clarity.
    `;

    try {
        const response = await ai.models.generateContent({
            model,
            contents: prompt,
            config: {
                responseMimeType: "application/json",
                responseSchema: {
                    type: Type.OBJECT,
                    properties: {
                        summary: { type: Type.STRING },
                        ideas: { type: Type.ARRAY, items: { type: Type.STRING } },
                        script: { type: Type.STRING }
                    }
                }
            }
        });
        
        const jsonText = response.text.trim();
        const parsed = JSON.parse(jsonText);
        return parsed as AIGeneratedContent;
    } catch (error) {
        console.error("Error generating ideas and script:", error);
        throw new Error("Failed to communicate with the Gemini API.");
    }
};
