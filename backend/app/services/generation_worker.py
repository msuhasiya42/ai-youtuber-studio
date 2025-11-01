"""
RAG-powered content generation worker for scripts and ideas.
"""
from celery_worker import app as celery_app
from app.services.llm_provider import get_llm_provider
from app.services.vector_store import get_vector_store
from typing import Optional, Dict, List
import json


@celery_app.task
def generate_summary_and_ideas(transcript_excerpt: str) -> dict:
    """Legacy function - kept for backward compatibility"""
    provider = get_llm_provider()
    prompt = (
        "You are an expert YouTube strategist. Given transcript excerpts and metadata,\n"
        "return: 1) summary (3 sentences) 2) 3 creative video ideas relevant to the channel style\n"
        "3) a script outline for the top idea (Hook → Intro → Body → CTA)\n"
        "Output JSON only: { \"summary\": \"\", \"ideas\": [], \"outline\": \"\" }\n\n"
        f"Transcript: {transcript_excerpt}"
    )
    text = provider.generate(prompt)
    return {"raw": text}


@celery_app.task
def generate_script_with_rag(
    topic: str,
    channel_id: int,
    tone: Optional[str] = None,
    minutes: Optional[int] = 8,
    video_format: str = "standard"
) -> Dict:
    """
    Generate a video script using RAG to retrieve context from successful videos.

    Args:
        topic: Video topic/idea
        channel_id: Channel ID for context retrieval
        tone: Script tone (casual, professional, educational, etc.)
        minutes: Target duration in minutes
        video_format: 'standard', 'short', or 'tutorial'

    Returns:
        Dictionary with script and metadata
    """
    llm_provider = get_llm_provider()
    vector_store = get_vector_store()

    # Retrieve relevant context from vector store
    search_query = f"successful video about {topic} with engaging hook and high retention"
    relevant_chunks = vector_store.search(query=search_query, n_results=5)

    # Build context from retrieved chunks
    context_sections = []
    for i, chunk in enumerate(relevant_chunks[:3], 1):
        context_sections.append(
            f"Example {i} (from a video with {chunk['metadata'].get('views', 0):,} views):\n{chunk['text']}"
        )

    context = "\n\n".join(context_sections) if context_sections else "No previous examples available."

    # Build prompt based on format
    if video_format == "short":
        format_instructions = """
Create a 60-second YouTube Short script with:
- Hook (first 2 seconds)
- Body (key points with fast pacing)
- CTA (call-to-action at end)

Use short sentences, visual cues, and captions."""
    elif video_format == "tutorial":
        format_instructions = f"""
Create a {minutes}-minute tutorial script with:
- Hook (problem statement)
- Introduction (what they'll learn)
- Step-by-step guide (numbered steps)
- Conclusion (recap + CTA)

Be clear and actionable."""
    else:
        format_instructions = f"""
Create a {minutes}-minute video script with:
- Hook (first 10 seconds to grab attention)
- Introduction (set expectations)
- Body (main content with engagement moments)
- Conclusion (recap + strong CTA)

Keep it engaging and conversational."""

    tone_instruction = f"Tone: {tone}" if tone else "Tone: Conversational and engaging"

    prompt = f"""You are an expert YouTube script writer. Generate a video script based on successful patterns from the channel.

TOPIC: {topic}

{tone_instruction}

{format_instructions}

CONTEXT FROM SUCCESSFUL VIDEOS:
{context}

IMPORTANT:
- Use proven engagement techniques from the examples above
- Include timestamps for key moments (e.g., [0:10])
- Add [VISUAL] cues where needed
- Make the hook compelling (reference examples)
- Use pattern interrupts every 30-60 seconds

Return ONLY valid JSON in this format:
{{
  "title_suggestion": "Engaging title based on topic",
  "hook": "First 10 seconds script",
  "introduction": "Introduction section",
  "body": [
    {{"timestamp": "0:30", "content": "Section 1 content"}},
    {{"timestamp": "2:00", "content": "Section 2 content"}}
  ],
  "conclusion": "Conclusion with CTA",
  "visual_cues": ["List of visual suggestions"],
  "estimated_retention_points": ["Key moments that will retain viewers"]
}}

Generate the script now:"""

    try:
        response = llm_provider.generate(prompt)

        # Try to extract JSON from response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start != -1 and json_end > json_start:
            script_json = json.loads(response[json_start:json_end])
            return {
                "status": "success",
                "script": script_json,
                "topic": topic,
                "format": video_format,
                "duration_minutes": minutes,
                "context_used": len(relevant_chunks)
            }
        else:
            # Fallback: return raw response
            return {
                "status": "success",
                "script": {"raw_script": response},
                "topic": topic,
                "format": video_format,
                "note": "Could not parse JSON, returning raw script"
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "topic": topic
        }


@celery_app.task
def generate_script(outline: str, tone: Optional[str] = None, minutes: Optional[int] = 8) -> str:
    """Legacy script generation - kept for backward compatibility"""
    provider = get_llm_provider()
    prompt = (
        f"Write a full YouTube script (~{minutes} minutes) with tone: {tone or 'default'}.\n"
        f"Use this outline: {outline}"
    )
    return provider.generate(prompt)


