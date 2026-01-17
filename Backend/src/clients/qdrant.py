"""Qdrant client wrapper for vector database operations."""

from typing import List, Optional

from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import (
    CollectionStatus,
    Distance,
    HnswConfigDiff,
    OptimizersConfigDiff,
    PointStruct,
    VectorParams,
)
from structlog import get_logger

from src.config.settings import get_settings

logger = get_logger(__name__)

# Collection configuration
COLLECTION_NAME = "prompt_embeddings"
VECTOR_SIZE = 1536  # text-embedding-3-small dimension


class QdrantClientWrapper:
    """Wrapper for Qdrant client with connection management."""

    def __init__(self, client: Optional[QdrantClient] = None):
        """
        Initialize Qdrant client wrapper.

        Args:
            client: Optional QdrantClient instance. If None, creates a new one.
        """
        if client is None:
            settings = get_settings()
            qdrant_config = settings.database.vector_db.qdrant

            if not qdrant_config:
                raise ValueError("Qdrant configuration not found")

            # Create client
            self.client = QdrantClient(
                url=f"http://{qdrant_config.host}:{qdrant_config.port}",
                api_key=qdrant_config.api_key,
            )

            logger.info(
                "Qdrant client initialized",
                host=qdrant_config.host,
                port=qdrant_config.port,
            )
        else:
            self.client = client

    def ensure_collection(self) -> bool:
        """
        Ensure collection exists with correct configuration.

        Returns:
            True if collection exists or was created, False otherwise
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if COLLECTION_NAME in collection_names:
                logger.info("Collection already exists", collection=COLLECTION_NAME)
                return True

            # Create collection
            logger.info("Creating collection", collection=COLLECTION_NAME)

            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
                hnsw_config=HnswConfigDiff(
                    m=16,  # Number of connections
                    ef_construct=100,  # Size of the candidate list
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=10000,  # Index when this many points
                ),
            )

            logger.info("Collection created successfully", collection=COLLECTION_NAME)
            return True

        except Exception as e:
            logger.error("Error ensuring collection", error=str(e), collection=COLLECTION_NAME)
            return False

    def get_collection_info(self) -> Optional[dict]:
        """
        Get collection information.

        Returns:
            Collection info dictionary or None if collection doesn't exist
        """
        try:
            info = self.client.get_collection(COLLECTION_NAME)
            return {
                "name": info.name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
            }
        except Exception as e:
            logger.error("Error getting collection info", error=str(e))
            return None

    def upsert_points(self, points: List[PointStruct]) -> bool:
        """
        Upsert points into collection.

        Args:
            points: List of PointStruct objects

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.debug("Points upserted", count=len(points), collection=COLLECTION_NAME)
            return True
        except Exception as e:
            logger.error("Error upserting points", error=str(e), count=len(points))
            return False

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
    ) -> List[dict]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Optional minimum similarity score

        Returns:
            List of search results with id and score
        """
        try:
            search_result = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            results = [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload or {},
                }
                for hit in search_result
            ]

            logger.debug(
                "Search completed",
                results_count=len(results),
                limit=limit,
                score_threshold=score_threshold,
            )

            return results

        except Exception as e:
            logger.error("Error searching", error=str(e))
            return []

    def delete_points(self, point_ids: List[str]) -> bool:
        """
        Delete points from collection.

        Args:
            point_ids: List of point IDs to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=point_ids,
            )
            logger.debug("Points deleted", count=len(point_ids), collection=COLLECTION_NAME)
            return True
        except Exception as e:
            logger.error("Error deleting points", error=str(e), count=len(point_ids))
            return False


class AsyncQdrantClientWrapper:
    """Async wrapper for Qdrant client."""

    def __init__(self, client: Optional[AsyncQdrantClient] = None):
        """
        Initialize async Qdrant client wrapper.

        Args:
            client: Optional AsyncQdrantClient instance. If None, creates a new one.
        """
        if client is None:
            settings = get_settings()
            qdrant_config = settings.database.vector_db.qdrant

            if not qdrant_config:
                raise ValueError("Qdrant configuration not found")

            # Create async client
            self.client = AsyncQdrantClient(
                url=f"http://{qdrant_config.host}:{qdrant_config.port}",
                api_key=qdrant_config.api_key,
            )

            logger.info(
                "Async Qdrant client initialized",
                host=qdrant_config.host,
                port=qdrant_config.port,
            )
        else:
            self.client = client

    async def ensure_collection(self) -> bool:
        """
        Ensure collection exists with correct configuration.

        Returns:
            True if collection exists or was created, False otherwise
        """
        try:
            # Check if collection exists
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if COLLECTION_NAME in collection_names:
                logger.info("Collection already exists", collection=COLLECTION_NAME)
                return True

            # Create collection
            logger.info("Creating collection", collection=COLLECTION_NAME)

            await self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
                hnsw_config=HnswConfigDiff(
                    m=16,  # Number of connections
                    ef_construct=100,  # Size of the candidate list
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=10000,  # Index when this many points
                ),
            )

            logger.info("Collection created successfully", collection=COLLECTION_NAME)
            return True

        except Exception as e:
            logger.error("Error ensuring collection", error=str(e), collection=COLLECTION_NAME)
            return False

    async def get_collection_info(self) -> Optional[dict]:
        """
        Get collection information.

        Returns:
            Collection info dictionary or None if collection doesn't exist
        """
        try:
            info = await self.client.get_collection(COLLECTION_NAME)
            return {
                "name": info.name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
            }
        except Exception as e:
            logger.error("Error getting collection info", error=str(e))
            return None

    async def upsert_points(self, points: List[PointStruct]) -> bool:
        """
        Upsert points into collection.

        Args:
            points: List of PointStruct objects

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.client.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.debug("Points upserted", count=len(points), collection=COLLECTION_NAME)
            return True
        except Exception as e:
            logger.error("Error upserting points", error=str(e), count=len(points))
            return False

    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
    ) -> List[dict]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Optional minimum similarity score

        Returns:
            List of search results with id and score
        """
        try:
            search_result = await self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            results = [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload or {},
                }
                for hit in search_result
            ]

            logger.debug(
                "Search completed",
                results_count=len(results),
                limit=limit,
                score_threshold=score_threshold,
            )

            return results

        except Exception as e:
            logger.error("Error searching", error=str(e))
            return []

    async def delete_points(self, point_ids: List[str]) -> bool:
        """
        Delete points from collection.

        Args:
            point_ids: List of point IDs to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=point_ids,
            )
            logger.debug("Points deleted", count=len(point_ids), collection=COLLECTION_NAME)
            return True
        except Exception as e:
            logger.error("Error deleting points", error=str(e), count=len(point_ids))
            return False


# Global client instances
_qdrant_client: Optional[QdrantClientWrapper] = None
_async_qdrant_client: Optional[AsyncQdrantClientWrapper] = None


def get_qdrant_client() -> QdrantClientWrapper:
    """
    Get global Qdrant client instance.

    Returns:
        QdrantClientWrapper instance
    """
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClientWrapper()
    return _qdrant_client


def get_async_qdrant_client() -> AsyncQdrantClientWrapper:
    """
    Get global async Qdrant client instance.

    Returns:
        AsyncQdrantClientWrapper instance
    """
    global _async_qdrant_client
    if _async_qdrant_client is None:
        _async_qdrant_client = AsyncQdrantClientWrapper()
    return _async_qdrant_client

