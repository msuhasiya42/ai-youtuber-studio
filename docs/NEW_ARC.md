# Backend Architecture - AI YouTuber Studio

This document outlines the architecture of the AI YouTuber Studio backend, detailing its core components, data flow, technologies, and deployment strategy. The backend is designed to ingest YouTube video data, process it for insights, manage user channels, and serve analytics to the frontend.

## 1. Overview

The backend is built primarily with Python (FastAPI) and leverages a robust ecosystem of services for asynchronous processing, data storage, and AI capabilities. It acts as the central hub for interacting with YouTube APIs, managing database operations, orchestrating heavy-lifting tasks via Celery, and integrating with AI/ML models for advanced insights.

## 2. Tech Stack

*   **API Framework:** FastAPI (Python 3.11+)
*   **Database:** PostgreSQL (AWS RDS) - for structured data (videos, channels, analytics, insights)
*   **Message Broker/Cache:** Redis (Docker) - used by Celery for task queuing and results
*   **Vector Database:** ChromaDB (EC2) - for storing and retrieving vector embeddings of video captions/transcripts
*   **Object Storage:** AWS S3 - for storing video assets (thumbnails, raw captions, generated transcripts)
*   **Asynchronous Task Queue:** Celery - for offloading long-running tasks like video processing and analytics syncing
*   **ORM:** SQLAlchemy with Alembic for database migrations
*   **External APIs:** YouTube Data API v3, YouTube Analytics API v2
*   **LLM Integration:** OpenAI / Google Gemini (via `app/services/providers/`)
*   **Containerization:** Docker, Docker Compose

## 3. Core Components (Services)

The backend is composed of several inter-communicating services, primarily orchestrated via Docker Compose.

### 3.1. FastAPI Application (`ai-youtuber-backend`)

*   **Purpose:** Exposes the RESTful API endpoints for the frontend, handles user authentication, and interacts with the database and Celery workers.
*   **Key Responsibilities:**
    *   User authentication and authorization (Google OAuth, JWT).
    *   Managing channel and video metadata.
    *   Triggering video processing and analytics syncing tasks.
    *   Serving analytics and AI-generated insights to the frontend.
*   **Key Files:**
    *   `app/main.py`: Main FastAPI application entry point, router registration.
    *   `app/api/auth.py`: User authentication, Google OAuth callback.
    *   `app/api/channels.py`: Endpoints for managing YouTube channels, triggering video syncing.
    *   `app/api/videos.py`: Endpoints for video metadata.
    *   `app/api/analytics.py`: Endpoints for fetching YouTube Analytics data and pattern analysis.
    *   `app/api/insights.py`: Endpoints for AI-generated insights.
    *   `app/services/youtube_client.py`: Wrapper for YouTube Data API interactions.
    *   `app/services/youtube_analytics_client.py`: Wrapper for YouTube Analytics API interactions.
    *   `app/services/llm_provider.py` & `app/services/providers/`: LLM integration.

### 3.2. Celery Worker (`ai-youtuber-worker`)

*   **Purpose:** Executes long-running, CPU-intensive, or asynchronous tasks in the background, offloading them from the main FastAPI application.
*   **Key Responsibilities:**
    *   Processing video pipelines (fetching captions, indexing).
    *   Synchronizing YouTube Analytics data.
    *   Generating advanced pattern analysis and LLM-powered insights.
*   **Key Files:**
    *   `celery_worker.py`: Celery application instance.
    *   `app/services/pipeline_worker.py`: Orchestrates the video processing steps (now without `yt-dlp`).
    *   `app/services/transcribe_worker.py`: (Will be adapted/refactored) Responsible for processing captions/transcripts.
    *   `app/services/analytics_sync_worker.py`: Celery tasks for syncing various YouTube Analytics data.
    *   `app/services/advanced_pattern_analyzer.py`: Contains the logic for statistical pattern analysis.
    *   `app/services/insights_generation_prompts.py`: LLM prompt templates.

### 3.3. Redis (`ai-youtuber-redis`)

*   **Purpose:** Serves as the message broker for Celery (to queue and distribute tasks) and can also be used as a cache.
*   **Role:** Essential for the asynchronous nature of the video processing and analytics syncing.

### 3.4. PostgreSQL (AWS RDS)

*   **Purpose:** The primary relational database for storing all structured data.
*   **Key Data Stored:**
    *   `channels`: YouTube channel metadata.
    *   `videos`: Video metadata, processing status, analytics fields, raw captions, insights JSON.
    *   `video_analytics_daily`: Daily time-series metrics for videos.
    *   `video_retention_curves`: Audience retention data.
    *   `video_traffic_sources`: Traffic source breakdown.
    *   `channel_demographics`: Age, gender, geography data for channels.
    *   `ai_insights`: Cached LLM-generated insights.
    *   `frame_samples`: Metadata for sampled video frames.
*   **Tools:** SQLAlchemy ORM for application interaction, Alembic for migrations.

### 3.5. ChromaDB (`ai-youtuber-chroma`)

*   **Purpose:** A vector database used for storing and retrieving vector embeddings.
*   **Role:** Enables RAG (Retrieval Augmented Generation) by storing embeddings of video captions/transcripts for LLM-powered script generation and content recommendations.

### 3.6. AWS S3

*   **Purpose:** Object storage for large binary files.
*   **Key Data Stored:**
    *   Video thumbnails (or URLs if directly linked).
    *   Generated full