"""
ChromaDB vector store for semantic search of video transcripts.
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import json
from app.services.llm_provider import get_llm_provider
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Vector store for indexing and searching video transcripts"""

    def __init__(self):
        self.chroma_host = os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = int(os.getenv("CHROMA_PORT", "8001"))

        logger.info(f"Initializing VectorStore - ChromaDB at {self.chroma_host}:{self.chroma_port}")

        try:
            # Initialize ChromaDB client
            self.client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=Settings(anonymized_telemetry=False)
            )

            # Get or create collection for transcripts
            self.collection = self.client.get_or_create_collection(
                name="video_transcripts",
                metadata={"description": "YouTube video transcripts with metadata"}
            )

            collection_count = self.collection.count()
            logger.info(f"VectorStore initialized - collection: video_transcripts, existing chunks: {collection_count}")

            self.llm_provider = get_llm_provider()
        except Exception as e:
            logger.error(f"Failed to initialize VectorStore: {e}", exc_info=True)
            raise

    def chunk_transcript(self, transcript_text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Chunk transcript into smaller segments for embedding.

        Args:
            transcript_text: Full transcript text
            chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks for context preservation

        Returns:
            List of text chunks
        """
        logger.debug(f"Chunking transcript - text_length: {len(transcript_text)}, chunk_size: {chunk_size}, overlap: {overlap}")

        words = transcript_text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1  # +1 for space

            if current_length >= chunk_size:
                chunks.append(" ".join(current_chunk))
                # Keep last few words for overlap
                overlap_words = int(overlap / 10)  # Rough estimate
                current_chunk = current_chunk[-overlap_words:] if overlap_words > 0 else []
                current_length = sum(len(w) + 1 for w in current_chunk)

        # Add remaining chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logger.debug(f"Transcript chunked into {len(chunks)} segments")
        return chunks

    def index_transcript(
        self,
        video_id: str,
        youtube_video_id: str,
        transcript_data: Dict,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Index a video transcript in the vector store.

        Args:
            video_id: Database video ID
            youtube_video_id: YouTube video ID
            transcript_data: Transcript data with text and segments
            metadata: Additional metadata (views, likes, etc.)

        Returns:
            Number of chunks indexed
        """
        logger.info(f"Indexing transcript for video {youtube_video_id} (db_id: {video_id})")

        transcript_text = transcript_data.get("text", "")

        if not transcript_text:
            logger.error(f"Transcript text is empty for video {youtube_video_id}")
            raise ValueError("Transcript text is empty")

        try:
            # Chunk the transcript
            chunks = self.chunk_transcript(transcript_text)
            logger.info(f"Generated {len(chunks)} chunks for video {youtube_video_id}")

            # Generate embeddings
            logger.debug(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = self.llm_provider.embed(chunks)
            logger.debug(f"Embeddings generated successfully")

            # Prepare metadata for each chunk
            chunk_ids = []
            chunk_metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{youtube_video_id}_chunk_{i}"
                chunk_ids.append(chunk_id)

                chunk_metadata = {
                    "video_id": str(video_id),
                    "youtube_video_id": youtube_video_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "language": transcript_data.get("language", "unknown"),
                }

                # Add optional metadata
                if metadata:
                    chunk_metadata.update({
                        "views": metadata.get("views", 0),
                        "likes": metadata.get("likes", 0),
                        "title": metadata.get("title", "")[:100],  # Truncate long titles
                        "duration": metadata.get("duration", 0),
                    })

                chunk_metadatas.append(chunk_metadata)

            # Add to ChromaDB
            logger.debug(f"Adding {len(chunks)} chunks to ChromaDB collection")
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=chunk_metadatas
            )

            logger.info(
                f"Successfully indexed {len(chunks)} chunks for video {youtube_video_id} "
                f"(title: {metadata.get('title', 'N/A')[:50] if metadata else 'N/A'})"
            )

            return len(chunks)
        except Exception as e:
            logger.error(f"Error indexing transcript for video {youtube_video_id}: {e}", exc_info=True)
            raise

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for relevant transcript segments using semantic search.

        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Metadata filters (e.g., {"youtube_video_id": "abc123"})

        Returns:
            List of matching chunks with metadata
        """
        logger.info(f"Searching vector store - query: '{query[:50]}...', n_results: {n_results}, filters: {filter_metadata}")

        try:
            # Generate query embedding
            logger.debug("Generating query embedding")
            query_embedding = self.llm_provider.embed([query])[0]

            # Search ChromaDB
            logger.debug("Querying ChromaDB collection")
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata if filter_metadata else None
            )

            # Format results
            formatted_results = []
            if results and results.get("documents"):
                for i in range(len(results["documents"][0])):
                    formatted_results.append({
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None,
                    })

            logger.info(f"Search returned {len(formatted_results)} results")
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching vector store: {e}", exc_info=True)
            raise

    def get_video_context(self, youtube_video_id: str, max_chunks: int = 10) -> str:
        """
        Get full context for a video by retrieving all its chunks.

        Args:
            youtube_video_id: YouTube video ID
            max_chunks: Maximum number of chunks to retrieve

        Returns:
            Combined text from all chunks
        """
        logger.debug(f"Retrieving context for video {youtube_video_id} (max_chunks: {max_chunks})")

        try:
            results = self.collection.get(
                where={"youtube_video_id": youtube_video_id},
                limit=max_chunks
            )

            if not results or not results.get("documents"):
                logger.warning(f"No chunks found for video {youtube_video_id}")
                return ""

            # Sort by chunk index and combine
            chunks_with_meta = list(zip(results["documents"], results["metadatas"]))
            chunks_with_meta.sort(key=lambda x: x[1].get("chunk_index", 0))

            combined_text = " ".join([chunk[0] for chunk in chunks_with_meta])
            logger.info(f"Retrieved {len(chunks_with_meta)} chunks for video {youtube_video_id} (total length: {len(combined_text)} chars)")

            return combined_text
        except Exception as e:
            logger.error(f"Error retrieving context for video {youtube_video_id}: {e}", exc_info=True)
            raise

    def delete_video(self, youtube_video_id: str):
        """Delete all chunks for a specific video"""
        logger.info(f"Deleting all chunks for video {youtube_video_id}")

        try:
            # Get all chunk IDs for this video
            results = self.collection.get(
                where={"youtube_video_id": youtube_video_id}
            )

            if results and results.get("ids"):
                chunk_count = len(results["ids"])
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {chunk_count} chunks for video {youtube_video_id}")
            else:
                logger.warning(f"No chunks found to delete for video {youtube_video_id}")
        except Exception as e:
            logger.error(f"Error deleting chunks for video {youtube_video_id}: {e}", exc_info=True)
            raise

    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector store collection"""
        logger.debug("Retrieving collection statistics")

        try:
            count = self.collection.count()
            stats = {
                "total_chunks": count,
                "collection_name": self.collection.name,
            }
            logger.info(f"Collection stats - name: {self.collection.name}, total_chunks: {count}")
            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}", exc_info=True)
            raise


# Singleton instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get or create vector store singleton"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
