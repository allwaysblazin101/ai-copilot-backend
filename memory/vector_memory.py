import faiss
import numpy as np
import asyncio
from datetime import datetime
from openai import AsyncOpenAI
from backend.config.settings import settings
from backend.utils.logger import logger

class VectorMemory:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        self.dimension = 1536  # Standard for text-embedding-3-small
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []  # Stores the actual text strings

    async def add_documents(self, texts: list[str]):
        """Embeds text and adds it to the FAISS index."""
        if not texts or not isinstance(texts, list):
            return
            
        try:
            response = await self.client.embeddings.create(
                input=texts, 
                model="text-embedding-3-small"
            )
            vectors = np.array([d.embedding for d in response.data]).astype('float32')
            
            self.index.add(vectors)
            self.metadata.extend(texts)
            return True
        except Exception as e:
            logger.error(f"Error adding to Vector Memory: {e}")
            return False
    
    async def add_interaction(self, query: str, answer: str):
        """
        Chunks the interaction and adds it to the vector store using the existing add_documents flow.
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            # We format as a single string to keep your metadata list consistent (strings only)
            text_to_embed = f"[{timestamp}] User: {query} | Assistant: {answer}"
            
            # Use the internal method to handle embedding and FAISS indexing
            return await self.add_documents([text_to_embed])
        except Exception as e:
            logger.error(f"Vector interaction storage error: {e}")
            return False

    async def search(self, query: str, limit: int = 3) -> list[str]:
        """Searches long-term memory for relevant context."""
        if self.index.ntotal == 0:
            return []

        try:
            resp = await self.client.embeddings.create(
                input=[query], 
                model="text-embedding-3-small"
            )
            
            query_vector = np.array([resp.data[0].embedding]).astype('float32')
            _, indices = self.index.search(query_vector, limit)
            
            results = []
            for i in indices[0]:
                if i != -1 and i < len(self.metadata):
                    results.append(self.metadata[i])
            
            return results
        except Exception as e:
            logger.error(f"Vector Search Error: {e}")
            return []

    def clear(self):
        """Reset memory index."""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
