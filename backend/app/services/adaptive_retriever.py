"""Adaptive retrieval service for multi-step, iterative context refinement."""

import logging
from typing import Any

from ..models.schemas import CodeChunk, RetrievalStrategy
from .retriever import RAGRetriever, RetrievedChunk

logger = logging.getLogger(__name__)


class AdaptiveRetriever:
    """
    Orchestrates multi-step, iterative retrieval refinement.

    Wraps RAGRetriever and implements adaptive strategies:
    - Single-round retrieval (fast, simple queries)
    - Iterative retrieval (complex queries, refines until satisfied)
    - Tracks queries used and results found
    """

    def __init__(self, retriever: RAGRetriever):
        """
        Initialize the AdaptiveRetriever.

        Args:
            retriever: Base RAGRetriever instance to use
        """
        self.retriever = retriever
        self.max_iterations = 3
        self.min_satisfaction_threshold = 0.7

    @staticmethod
    def _convert_retrieved_to_chunk(retrieved: RetrievedChunk) -> CodeChunk:
        """Convert RetrievedChunk dataclass to CodeChunk Pydantic model."""
        return CodeChunk(
            id=retrieved.id,
            file=retrieved.file,
            language=retrieved.language,
            start_line=retrieved.start_line,
            end_line=retrieved.end_line,
            type=retrieved.type or "unknown",
            content=retrieved.content,
            relevance_score=retrieved.relevance_score,
        )

    async def retrieve_with_strategy(
        self,
        query: str,
        strategy: RetrievalStrategy,
        score_threshold: float = 0.3,
    ) -> tuple[list[CodeChunk], list[str], int]:
        """
        Retrieve context using an adaptive strategy.

        Args:
            query: The original (or decomposed) query
            strategy: RetrievalStrategy defining how to retrieve
            score_threshold: Minimum relevance score

        Returns:
            Tuple of:
            - list[CodeChunk]: Retrieved chunks
            - list[str]: All queries executed
            - int: Number of retrieval rounds
        """
        logger.info(
            f"Starting adaptive retrieval. Strategy: {strategy.retrieval_type}, "
            f"max_rounds: {strategy.max_retrieval_rounds}"
        )

        all_chunks: dict[str, CodeChunk] = {}
        queries_used: list[str] = [query]
        round_num = 0

        if strategy.retrieval_type == "single_round":
            retrieved_chunks = self.retriever.retrieve(
                query=query,
                top_k=strategy.top_k_per_round,
                score_threshold=score_threshold,
            )
            chunks = [self._convert_retrieved_to_chunk(c) for c in retrieved_chunks]
            all_chunks.update({chunk.id: chunk for chunk in chunks})
            round_num = 1

        elif strategy.retrieval_type == "iterative":
            round_num = await self._iterative_retrieval(
                query=query,
                strategy=strategy,
                score_threshold=score_threshold,
                all_chunks=all_chunks,
                queries_used=queries_used,
            )

        result_chunks = list(all_chunks.values())
        logger.info(
            f"Retrieval complete. Rounds: {round_num}, "
            f"Total chunks: {len(result_chunks)}, "
            f"Queries used: {len(queries_used)}"
        )

        return result_chunks, queries_used, round_num

    async def _iterative_retrieval(
        self,
        query: str,
        strategy: RetrievalStrategy,
        score_threshold: float,
        all_chunks: dict[str, CodeChunk],
        queries_used: list[str],
    ) -> int:
        """Execute iterative retrieval refinement."""
        for round_num in range(1, strategy.max_retrieval_rounds + 1):
            logger.info(f"Retrieval round {round_num}/{strategy.max_retrieval_rounds}")

            retrieved_chunks = self.retriever.retrieve(
                query=query,
                top_k=strategy.top_k_per_round,
                score_threshold=score_threshold,
            )
            chunks = [self._convert_retrieved_to_chunk(c) for c in retrieved_chunks]

            new_chunks = 0
            for chunk in chunks:
                if chunk.id not in all_chunks:
                    all_chunks[chunk.id] = chunk
                    new_chunks += 1

            logger.info(f"Round {round_num}: Found {len(chunks)} results, {new_chunks} new")

            if new_chunks == 0 and round_num > 1:
                logger.info("No new results found; stopping iterative retrieval")
                break

            if round_num < strategy.max_retrieval_rounds and len(all_chunks) > 0:
                refined_query = await self._generate_refined_query(
                    original_query=query,
                    round_num=round_num,
                    current_chunks=list(all_chunks.values()),
                )

                if refined_query and refined_query != query:
                    query = refined_query
                    queries_used.append(refined_query)
                    logger.info(f"Refined query for round {round_num + 1}: {refined_query[:80]}...")

        return round_num

    async def _generate_refined_query(
        self,
        original_query: str,
        round_num: int,
        current_chunks: list[CodeChunk],
    ) -> str | None:
        """
        Generate a refined query based on current results.

        For now, returns None (no refinement). Can be enhanced to use Claude
        for intelligent query refinement.
        """
        if not current_chunks:
            return None

        logger.debug(
            f"Query refinement opportunity at round {round_num} "
            f"({len(current_chunks)} chunks so far)"
        )

        return None

    async def retrieve_with_refinement(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
        enable_iterative: bool = False,
    ) -> tuple[list[CodeChunk], list[str], int]:
        """
        Convenience method: retrieve with optional refinement.

        Args:
            query: Query string
            top_k: Results per round
            score_threshold: Minimum score
            enable_iterative: Use iterative strategy

        Returns:
            Tuple of (chunks, queries_used, num_rounds)
        """
        strategy = RetrievalStrategy(
            retrieval_type="iterative" if enable_iterative else "single_round",
            top_k_per_round=top_k,
            max_retrieval_rounds=3 if enable_iterative else 1,
        )

        return await self.retrieve_with_strategy(
            query=query,
            strategy=strategy,
            score_threshold=score_threshold,
        )
