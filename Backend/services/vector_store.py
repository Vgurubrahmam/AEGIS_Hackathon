"""
AEGIS — Vector Store Service
ChromaDB wrapper with local sentence-transformers embeddings.
Used by VerificationAgent for RAG-based similarity search.
"""

import logging
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger("aegis.vector_store")

# Chroma persistent directory
CHROMA_DIR = "./chroma_data"
COLLECTION_NAME = "aegis_incidents"


class VectorStoreService:
    """ChromaDB + sentence-transformers embedding wrapper."""

    def __init__(self):
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection = None
        self._embedding_fn = None

    def initialize(self):
        """
        Initialize ChromaDB client and collection.
        Called once during app startup (lifespan).
        """
        logger.info("Initializing ChromaDB with sentence-transformers embeddings...")

        # Use sentence-transformers for local embeddings (no API key needed)
        self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Persistent local storage
        self._client = chromadb.PersistentClient(path=CHROMA_DIR)

        # Get or create the incidents collection
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"description": "AEGIS incident reports for RAG retrieval"},
        )

        logger.info(f"ChromaDB initialized. Collection '{COLLECTION_NAME}' has {self._collection.count()} documents.")

    def seed_incidents(self, incidents: list[dict]) -> None:
        """
        Seed historical incidents into ChromaDB.

        Args:
            incidents: List of dicts with keys: id, text, severity, need_type, landmark
        """
        if not incidents:
            return

        if not self._collection:
            logger.error("VectorStore not initialized. Call initialize() first.")
            return

        # Check if already seeded
        existing = self._collection.count()
        if existing > 0:
            logger.info(f"ChromaDB already has {existing} documents, skipping seed.")
            return

        ids = [inc["id"] for inc in incidents]
        documents = [inc["text"] for inc in incidents]
        metadatas = [
            {
                "severity": inc["severity"],
                "need_type": inc["need_type"],
                "landmark": inc.get("landmark", "unknown"),
            }
            for inc in incidents
        ]

        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Seeded {len(incidents)} incidents into ChromaDB.")

    def add_incident(self, incident_id: str, text: str, metadata: dict) -> None:
        """
        Add a single resolved incident to ChromaDB (for ongoing RAG enrichment).
        Called when an incident is marked as resolved.
        """
        if not self._collection:
            logger.error("VectorStore not initialized.")
            return

        self._collection.add(
            ids=[incident_id],
            documents=[text],
            metadatas=[metadata],
        )
        logger.debug(f"Added incident {incident_id} to ChromaDB.")

    def query_similar(self, text: str, n_results: int = 3) -> list[dict]:
        """
        Query ChromaDB for incidents similar to the given text.

        Returns:
            List of dicts with keys: id, text, distance, metadata
        """
        if not self._collection or self._collection.count() == 0:
            logger.debug("ChromaDB empty or not initialized, returning empty results.")
            return []

        results = self._collection.query(
            query_texts=[text],
            n_results=min(n_results, self._collection.count()),
        )

        similar = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                similar.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                })

        return similar


# Singleton instance
vector_store = VectorStoreService()
