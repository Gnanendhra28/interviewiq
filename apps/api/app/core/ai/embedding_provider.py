from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import AIProviderException


class EmbeddingMetadata(BaseModel):
    provider: str
    model: str
    dimension: int
    version: str = "v1"


class EmbeddingResult(BaseModel):
    embeddings: List[List[float]]
    metadata: EmbeddingMetadata


class EmbeddingProvider(ABC):
    """
    Abstract Embedding Provider Interface.
    Decouples vector embedding generation from specific LLM vendors while strictly
    validating model lineage metadata against configured database schema expectations.
    """

    @abstractmethod
    async def generate_embeddings(self, text_chunks: List[str]) -> EmbeddingResult:
        """Generate high-dimensional vector embeddings with explicit model metadata."""
        pass

    @abstractmethod
    def get_metadata(self) -> EmbeddingMetadata:
        """Return provider configuration metadata (model, dimension, version)."""
        pass

    def validate_schema_alignment(self, result: EmbeddingResult) -> None:
        """
        Validate that generated vector output metadata aligns with configured schema rules.
        Prevents silent misalignment between application config and database pgvector column dimensions.
        """
        if result.metadata.dimension != settings.EMBEDDING_DIMENSION:
            raise AIProviderException(
                f"Vector dimension mismatch! Provider generated {result.metadata.dimension} dimensions, "
                f"but DB schema expects EMBEDDING_DIMENSION={settings.EMBEDDING_DIMENSION}. "
                "Changing vector dimensions requires an explicit database migration & re-embedding cutover.",
                provider=result.metadata.provider
            )
        if result.metadata.model != settings.EMBEDDING_MODEL:
            raise AIProviderException(
                f"Embedding model mismatch! Provider output model '{result.metadata.model}' does not match "
                f"configured EMBEDDING_MODEL='{settings.EMBEDDING_MODEL}'.",
                provider=result.metadata.provider
            )
