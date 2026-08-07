import httpx
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.domain.knowledge.entities import KnowledgeDocument, BusinessRule
from app.infrastructure.repositories.postgres_repository import KnowledgeRepository
from app.core.config import settings


class KnowledgeService:
    """Enterprise Hybrid Retrieval Knowledge Engine.

    Combines database keyword queries and local Ollama semantic embeddings
    to resolve business context and rule associations.
    """

    def __init__(self, session: AsyncSession):
        self.repo = KnowledgeRepository(session)

    async def _get_embedding(self, text: str) -> List[float]:
        """Fetch text embeddings dynamically from local Ollama endpoint.

        Falls back to basic word hashing vector if Ollama is unreachable.
        """
        url = f"{settings.OLLAMA_HOST}/api/embeddings"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": text
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    return response.json().get("embedding", [])
        except Exception as e:
            logger.warning(f"Ollama embedding API unavailable: {e}. Falling back to token hash vectorizer.")
        
        # Fallback vector representation (128-dim word hash vectors)
        vec = [0.0] * 128
        for word in text.lower().split():
            h = hash(word) % 128
            vec[h] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = (vec / norm).tolist()
        return vec

    async def add_document(self, title: str, content: str, metadata: Dict[str, Any] = None) -> KnowledgeDocument:
        """Add document to index, pre-calculating local semantic embedding vector."""
        embedding = await self._get_embedding(content)
        db_doc = await self.repo.create(
            title=title,
            content=content,
            metadata_fields=metadata or {},
            embedding=embedding
        )
        return KnowledgeDocument.model_validate(db_doc)

    async def retrieve_hybrid(self, query_text: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Run Hybrid Retrieval (Keyword check + Cosine similarity) against indexed document base."""
        docs = await self.repo.list_all()
        if not docs:
            return []

        # 1. Compute cosine similarities
        query_emb = await self._get_embedding(query_text)
        q_vec = np.array(query_emb)

        scored_docs = []
        for doc in docs:
            doc_emb = doc.embedding
            semantic_score = 0.0
            
            if doc_emb and q_vec.any():
                d_vec = np.array(doc_emb)
                # Ensure dimension alignment
                if q_vec.shape == d_vec.shape:
                    dot = np.dot(q_vec, d_vec)
                    norm_q = np.linalg.norm(q_vec)
                    norm_d = np.linalg.norm(d_vec)
                    if norm_q > 0 and norm_d > 0:
                        semantic_score = float(dot / (norm_q * norm_d))

            # 2. Compute keyword match score (simple Jaccard overlap on titles/content)
            q_words = set(query_text.lower().split())
            d_words = set((doc.title + " " + doc.content).lower().split())
            overlap = q_words.intersection(d_words)
            keyword_score = len(overlap) / len(q_words) if q_words else 0.0

            # 3. Hybrid scoring (60% semantic similarity + 40% keyword overlap)
            hybrid_score = (semantic_score * 0.6) + (keyword_score * 0.4)

            scored_docs.append({
                "document": KnowledgeDocument.model_validate(doc),
                "score": round(hybrid_score, 4),
                "match_type": "semantic" if semantic_score > 0.5 else "keyword"
            })

        # Sort descending by score
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:limit]
