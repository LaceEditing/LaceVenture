"""
Vector database implementation for semantic search of game memories.
"""
import json
import os
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models

from config import (
    VECTOR_DB_TYPE, VECTOR_DB_URL, VECTOR_DB_PORT,
    VECTOR_DIMENSIONS, EMBEDDING_MODEL, CAMPAIGNS_DIR
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector database for storing and retrieving game memories based on semantic similarity.
    """

    def __init__(self,
                 campaign_id: str,
                 db_type: str = VECTOR_DB_TYPE,
                 url: str = VECTOR_DB_URL,
                 port: int = VECTOR_DB_PORT,
                 dimensions: int = VECTOR_DIMENSIONS,
                 embedding_model: str = EMBEDDING_MODEL):
        """
        Initialize the vector store.

        Args:
            campaign_id: Unique identifier for the campaign
            db_type: Type of vector database to use
            url: URL for the vector database
            port: Port for the vector database
            dimensions: Dimensionality of the vectors
            embedding_model: Model to use for generating embeddings
        """
        self.campaign_id = campaign_id
        self.collection_name = f"campaign_{campaign_id}"
        self.db_type = db_type
        self.dimensions = dimensions

        # Initialize the embedding model
        self.embedder = SentenceTransformer(embedding_model)

        # Set up storage for local mode
        self.vectors = []
        self.metadata = []

        # Initialize data file paths for local storage
        self.data_dir = os.path.join(CAMPAIGNS_DIR, campaign_id, "vector_store")
        os.makedirs(self.data_dir, exist_ok=True)
        self.vector_file = os.path.join(self.data_dir, "vectors.json")

        # Load existing data if available
        if self.db_type == "local" and os.path.exists(self.vector_file):
            try:
                with open(self.vector_file, "r") as f:
                    data = json.load(f)
                    self.vectors = data.get("vectors", [])
                    self.metadata = data.get("metadata", [])
                logger.info(f"Loaded {len(self.vectors)} vectors from local storage")
            except Exception as e:
                logger.error(f"Error loading vectors from local storage: {e}")

        # Only set up Qdrant client if we're using Qdrant
        if db_type == "qdrant":
            try:
                self.client = QdrantClient(url=url, port=port)
                self._setup_collection()
            except Exception as e:
                logger.error(f"Error connecting to Qdrant: {e}")
                logger.info("Falling back to local vector store")
                self.db_type = "local"
        elif db_type == "pinecone":
            # Implementation for Pinecone would go here
            logger.warning("Pinecone not implemented, falling back to local vector store")
            self.db_type = "local"

    def _setup_collection(self):
        """Set up the collection in the vector database."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.dimensions,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error setting up collection: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        return self.embedder.encode(text).tolist()

    def store_memory(self, text: str, metadata: Dict[str, Any]) -> str:
        """
        Store a memory in the vector database.

        Args:
            text: Text content of the memory
            metadata: Additional data about the memory

        Returns:
            ID of the stored memory
        """
        vector = self.embed_text(text)
        memory_id = str(uuid.uuid4())

        if self.db_type == "qdrant":
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        models.PointStruct(
                            id=memory_id,
                            vector=vector,
                            payload={
                                "text": text,
                                "type": metadata.get("type", "general"),
                                "timestamp": metadata.get("timestamp"),
                                "entities": metadata.get("entities", []),
                                "importance": metadata.get("importance", 0.5),
                                "source": metadata.get("source", "game_event"),
                                **{k: v for k, v in metadata.items() if
                                   k not in ["type", "timestamp", "entities", "importance", "source"]}
                            }
                        )
                    ]
                )
                logger.info(f"Stored memory: {memory_id}")
                return memory_id
            except Exception as e:
                logger.error(f"Error storing memory: {e}")
                # Fall back to local storage if Qdrant fails
                self.db_type = "local"
                full_metadata = {
                    "id": memory_id,
                    "text": text,
                    **metadata
                }
                self.vectors.append(vector)
                self.metadata.append(full_metadata)
                self._save_local_data()
                return memory_id
        elif self.db_type == "local":
            self.vectors.append(vector)
            full_metadata = {
                "id": memory_id,
                "text": text,
                **metadata
            }
            self.metadata.append(full_metadata)
            self._save_local_data()
            return memory_id

        return memory_id

    def _save_local_data(self) -> None:
        """Save vectors and metadata to local storage."""
        if self.db_type == "local":
            try:
                with open(self.vector_file, "w") as f:
                    json.dump({
                        "vectors": self.vectors,
                        "metadata": self.metadata
                    }, f)
                logger.info(f"Saved {len(self.vectors)} vectors to local storage")
            except Exception as e:
                logger.error(f"Error saving vectors to local storage: {e}")

    def search_similar(self, query: str, top_k: int = 10, filter_conditions: Optional[Dict] = None) -> List[
        Dict[str, Any]]:
        """
        Search for memories similar to the query.

        Args:
            query: Query text
            top_k: Number of results to return
            filter_conditions: Additional filtering conditions

        Returns:
            List of similar memories with metadata
        """
        query_vector = self.embed_text(query)

        if self.db_type == "qdrant":
            try:
                filter_dict = None
                if filter_conditions:
                    # Convert filter conditions to Qdrant filter format
                    filter_dict = self._build_qdrant_filter(filter_conditions)

                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                    query_filter=filter_dict
                )

                return [
                    {
                        "id": str(result.id),
                        "score": result.score,
                        **result.payload
                    }
                    for result in results
                ]
            except Exception as e:
                logger.error(f"Error searching for similar memories: {e}")
                raise
        elif self.db_type == "local":
            # Simple cosine similarity for local implementation
            results = []
            for i, vector in enumerate(self.vectors):
                similarity = self._cosine_similarity(query_vector, vector)
                results.append((similarity, i))

            # Sort by similarity (descending)
            results.sort(reverse=True)

            # Return top k results
            return [
                {
                    "id": self.metadata[i]["id"],
                    "score": score,
                    **self.metadata[i]
                }
                for score, i in results[:top_k]
            ]

        return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def _build_qdrant_filter(self, filter_conditions: Dict) -> models.Filter:
        """
        Build a Qdrant filter from the given conditions.

        Args:
            filter_conditions: Filter conditions

        Returns:
            Qdrant filter
        """
        qdrant_conditions = []

        for field, value in filter_conditions.items():
            if isinstance(value, list):
                # Handle list values (e.g., "entities": ["character_1", "character_2"])
                qdrant_conditions.append(
                    models.FieldCondition(
                        key=field,
                        match=models.MatchAny(any=value)
                    )
                )
            elif isinstance(value, dict) and ("min" in value or "max" in value):
                # Handle range values (e.g., "timestamp": {"min": 1600000000, "max": 1700000000})
                range_dict = {}
                if "min" in value:
                    range_dict["gte"] = value["min"]
                if "max" in value:
                    range_dict["lte"] = value["max"]

                qdrant_conditions.append(
                    models.FieldCondition(
                        key=field,
                        range=models.Range(**range_dict)
                    )
                )
            else:
                # Handle exact match
                qdrant_conditions.append(
                    models.FieldCondition(
                        key=field,
                        match=models.MatchValue(value=value)
                    )
                )

        return models.Filter(
            must=qdrant_conditions
        )

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from the vector database.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            True if successful
        """
        if self.db_type == "qdrant":
            try:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=[memory_id]
                    )
                )
                logger.info(f"Deleted memory: {memory_id}")
                return True
            except Exception as e:
                logger.error(f"Error deleting memory: {e}")
                return False
        elif self.db_type == "local":
            # Find the memory in the local store
            for i, meta in enumerate(self.metadata):
                if meta["id"] == memory_id:
                    # Remove it
                    self.metadata.pop(i)
                    self.vectors.pop(i)
                    return True
            return False

        return False

    def update_memory(self, memory_id: str, text: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update a memory in the vector database.

        Args:
            memory_id: ID of the memory to update
            text: New text content (if None, keep existing)
            metadata: New metadata (if None, keep existing)

        Returns:
            True if successful
        """
        # First retrieve the existing memory
        if self.db_type == "qdrant":
            try:
                existing = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[memory_id]
                )

                if not existing or not existing[0]:
                    logger.error(f"Memory not found: {memory_id}")
                    return False

                existing_payload = existing[0].payload

                # Update the vector if text is provided
                vector = None
                if text is not None:
                    vector = self.embed_text(text)
                    existing_payload["text"] = text

                # Update metadata if provided
                if metadata is not None:
                    for key, value in metadata.items():
                        existing_payload[key] = value

                # Perform the update
                if vector:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=[
                            models.PointStruct(
                                id=memory_id,
                                vector=vector,
                                payload=existing_payload
                            )
                        ]
                    )
                else:
                    # Update payload only
                    self.client.set_payload(
                        collection_name=self.collection_name,
                        payload=existing_payload,
                        points=[memory_id]
                    )

                logger.info(f"Updated memory: {memory_id}")
                return True
            except Exception as e:
                logger.error(f"Error updating memory: {e}")
                return False
        elif self.db_type == "local":
            # Find the memory in the local store
            for i, meta in enumerate(self.metadata):
                if meta["id"] == memory_id:
                    # Update text and vector if provided
                    if text is not None:
                        meta["text"] = text
                        self.vectors[i] = self.embed_text(text)

                    # Update metadata if provided
                    if metadata is not None:
                        for key, value in metadata.items():
                            meta[key] = value

                    return True
            return False

        return False