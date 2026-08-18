"""
RAG Retriever: Semantic search over indexed code using ChromaDB.

Encodes queries and retrieves relevant code chunks based on semantic similarity.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from langchain_core.embeddings import Embeddings
import chromadb
from .embedder_factory import create_embedder

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved code chunk with relevance score."""

    id: str
    file: str
    language: str
    start_line: int
    end_line: int
    content: str
    relevance_score: float
    type: str | None = None
    name: str | None = None


class RAGRetriever:
    """
    Retrieves relevant code chunks from ChromaDB based on semantic similarity.

    Uses embeddings to encode both queries and documents, returning top-k
    matches with relevance scores.
    """

    def __init__(
        self,
        embeddings: Embeddings | None = None,
        chroma_client=None,
        top_k: int = 5,
        db_path: str = "./chroma_db",
    ):
        """
        Initialize the retriever.

        Args:
            embeddings: LangChain Embeddings instance (if None, creates from settings)
            chroma_client: ChromaDB client instance
            top_k: Default number of chunks to retrieve
            db_path: Path to ChromaDB persistent storage
        """
        self.top_k = top_k
        self.collection = None
        self.embeddings = embeddings or create_embedder()

        try:
            # Initialize ChromaDB client if not provided
            if chroma_client:
                self.chroma_client = chroma_client
            else:
                # Ensure the directory exists before initializing ChromaDB
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=db_path)

            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="code_chunks",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB collection initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize ChromaDB: {str(e)}")
            self.collection = None

    def retrieve(
        self, query: str, top_k: int | None = None, score_threshold: float = 0.0
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant code chunks for a query.

        Args:
            query: Natural language query
            top_k: Number of chunks to retrieve (uses default if None)
            score_threshold: Minimum relevance score (0-1)

        Returns:
            List of RetrievedChunk objects sorted by relevance
        """
        if top_k is None:
            top_k = self.top_k

        logger.info(f"Retrieving chunks for query: {query[:100]}...")

        try:
            if not self.collection:
                logger.warning("No ChromaDB collection initialized, returning empty results")
                return []

            embedding = self.embeddings.embed_query(query)
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=top_k
            )

            chunks = []
            if results and results.get("documents") and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    distance = results["distances"][0][i] if results.get("distances") else 0

                    # Convert distance to similarity score (1 - distance for cosine)
                    relevance_score = max(0, 1 - distance)

                    file = metadata.get("file", "unknown")
                    start_line = int(metadata.get("start_line", 0))
                    end_line = int(metadata.get("end_line", 0))
                    chunk_id = f"{file}#{start_line}#{end_line}"

                    chunk = RetrievedChunk(
                        id=chunk_id,
                        file=file,
                        language=metadata.get("language", "unknown"),
                        start_line=start_line,
                        end_line=end_line,
                        content=doc,
                        relevance_score=relevance_score,
                        type=metadata.get("type"),
                        name=metadata.get("name"),
                    )
                    chunks.append(chunk)

            # Apply the score threshold, but never return nothing when the
            # index has data: vague/conversational queries score low against
            # code embeddings, so fall back to the best raw matches instead.
            filtered = [c for c in chunks if c.relevance_score >= score_threshold]
            if not filtered and chunks:
                logger.info(
                    f"All {len(chunks)} results below threshold {score_threshold}; "
                    "falling back to best raw matches"
                )
                return chunks

            return filtered

        except Exception as e:
            logger.error(f"Retrieval failed: {str(e)}")
            return []

    def add_chunks(self, chunks: list) -> int:
        """
        Add code chunks to the vector database.

        Args:
            chunks: List of CodeChunk objects

        Returns:
            Number of chunks added successfully
        """
        if not self.collection:
            logger.error("ChromaDB collection not initialized")
            return 0

        logger.info(f"Adding {len(chunks)} chunks to ChromaDB...")

        try:
            added_count = 0

            for i, chunk in enumerate(chunks):
                try:
                    # Create unique ID for the chunk
                    chunk_id = f"{chunk.file}#{chunk.start_line}#{chunk.end_line}"

                    # Prepare metadata
                    metadata = {
                        "file": chunk.file,
                        "language": chunk.language,
                        "start_line": str(chunk.start_line),
                        "end_line": str(chunk.end_line),
                        "type": chunk.type or "unknown",
                        "name": chunk.name or "unnamed",
                    }
                    embedding = self.embeddings.embed_query(chunk.content)

                    self.collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        documents=[chunk.content],
                        metadatas=[metadata],
                    )

                    added_count += 1

                    if (i + 1) % 100 == 0:
                        logger.info(f"Added {i + 1}/{len(chunks)} chunks")

                except Exception as e:
                    logger.error(
                        f"Failed to add chunk {chunk.file}:{chunk.start_line}: {str(e)}"
                    )

            logger.info(f"Successfully added {added_count}/{len(chunks)} chunks")
            return added_count

        except Exception as e:
            logger.error(f"Failed to add chunks: {str(e)}")
            return 0

    def clear(self) -> None:
        """Clear all chunks from the vector database."""
        try:
            if self.collection:
                # Delete all documents in the collection
                all_items = self.collection.get()
                if all_items and all_items.get("ids"):
                    self.collection.delete(ids=all_items["ids"])
                    logger.info(f"Cleared {len(all_items['ids'])} chunks from ChromaDB")
                else:
                    logger.info("No chunks to clear from ChromaDB")
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB: {str(e)}")
