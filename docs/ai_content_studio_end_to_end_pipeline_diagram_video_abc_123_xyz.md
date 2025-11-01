# AI Content Studio — End-to-End Pipeline

**Example video:** "How to Make a YouTube Short Go Viral in 2025" (id: `abc123xyz`)

Below is a single visual flow diagram (Mermaid) that shows the full data flow for one video through the pipeline you described, plus a short legend and notes on each step. Use this as the master reference for Phase 2 architecture and implementation details.

```mermaid
flowchart TD
  subgraph Ingest
    A[YouTube URL / Video ID\n(abc123xyz)] --> B[YouTube Data API (videos.list)\nmetadata: snippet, statistics, contentDetails]
    B --> DB1[(Postgres: video metadata)]
  end

  subgraph Download_Transcribe
    B --> C[yt-dlp (audio download)\nabc123xyz.mp3]
    C --> D[Whisper Transcription\nsegments + full text]
    D --> S3[(S3 / object store: audio + transcript JSON)]
    D --> DB2[(Postgres: transcript index/meta)]
  end

  subgraph Indexing
    D --> E[Chunking service\n(split into N-second or token chunks]
    E --> F[Embedding model (encoder)\n-> vector embeddings]
    F --> G[ChromaDB (vector collection)\nstore embeddings + metadata]
  end

  subgraph Analysis
    G --> H[Pattern Analysis Engine\n(aggregate across videos)]
    H --> DB3[(Postgres: aggregated insights)]
    H --> ML[Predictor / Title Scorer]
  end

  subgraph RAG_Generation
    G --> R[Retrieval (Chroma queries)\nfetch top-k chunks]
    R --> LLM[LLM (RAG prompt)\nscript generation & titles]
    LLM --> DB4[(Postgres: generated assets)]
  end

  subgraph Output
    DB1 & DB2 & DB3 & DB4 --> DASH[Dashboard / API \n(transcript, insights, scripts, titles)]
    DASH --> FE[Frontend: UI components\nrender transcript, comments, recommendations]
  end

  %% Controls & infra
  INFRA[Orchestration: Airflow / Prefect / Cron] --- B
  INFRA --- C
  INFRA --- E
  MON[Monitoring & Quotas / Rate-limiter] --- B
  MON --- F

  style DB1 fill:#f9f,stroke:#333,stroke-width:1px
  style DB2 fill:#f9f,stroke:#333,stroke-width:1px
  style DB3 fill:#f9f,stroke:#333,stroke-width:1px
  style DB4 fill:#f9f,stroke:#333,stroke-width:1px
  style S3 fill:#fffbcc,stroke:#333
  style G fill:#ccf,stroke:#333
  style LLM fill:#cfc,stroke:#333
```

---

## Legend & Notes
- **YouTube Data API**: fetches metadata (title, stats, publishedAt). Store as canonical source in Postgres.
- **yt-dlp**: download audio-only artifact. Store locally or stream to S3.
- **Whisper**: generate timestamped transcript (segments + full text). Store both JSON and raw text.
- **Chunking**: split transcript into semantically coherent chunks (time-based or token-based) and include metadata: `videoId`, `chunkId`, `start`, `end`, `text`.
- **Embedding**: call the chosen embedding model (OpenAI / local / other) and store vectors in ChromaDB with metadata.
- **Pattern Analysis**: offline job that computes cross-video features (duration, hook styles, retention markers) and writes to a normalized insights table.
- **Retrieval (RAG)**: at generation time, query ChromaDB for top-K relevant chunks and include results in the LLM prompt as context.
- **LLM generation**: use system + user + retrieved context to produce script, titles, CTAs, and predicted performance metrics. Persist outputs.
- **Dashboard / API**: provide endpoints returning structured JSON (metadata, transcript segments, insights, scripts, title recommendations).

---

## Operational considerations
- **Quota & throttling**: central rate-limiter for YouTube API calls, exponential backoff for 429 errors.
- **Idempotency**: video processing should be idempotent (use `videoId` as primary key) so you can resume or re-run safely.
- **Storage**: audio + transcript -> S3; embeddings -> ChromaDB; structured metadata & analytics -> Postgres.
- **Privacy & TOS**: respect YouTube terms; cache responsibly and include attribution.

---

If you want, I can now:
- Export this diagram as a PNG/SVG (for slide-ready images).
- Produce a Kubernetes/Helm microservices breakdown for each block.
- Expand any block into a step-by-step implementation checklist with exact commands, Dockerfiles, and example configs.

Tell me which of the three you want next and I will add it to the canvas.

