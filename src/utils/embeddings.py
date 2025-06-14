"""
Embedding Generator for Product Vectorization
Supports OpenAI and sentence-transformers
"""
import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from abc import ABC, abstractmethod
import asyncio
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class EmbeddingGenerator(ABC):
    """Abstract base class for embedding generators"""
    
    @abstractmethod
    async def generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        pass


class OpenAIEmbeddingGenerator(EmbeddingGenerator):
    """OpenAI embedding generator using text-embedding-3-large"""
    
    def __init__(self, model: str = "text-embedding-3-large"):
        self.model = model
        self.dimension = 3072 if "large" in model else 1536
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        try:
            # OpenAI has a limit on batch size
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = await openai.Embedding.acreate(
                    model=self.model,
                    input=batch
                )
                
                embeddings = [item["embedding"] for item in response["data"]]
                all_embeddings.extend(embeddings)
                
                # Rate limiting
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    def get_dimension(self) -> int:
        return self.dimension


class SentenceTransformerEmbeddingGenerator(EmbeddingGenerator):
    """Local embedding generator using sentence-transformers"""
    
    def __init__(self, model_name: str = "sentence-transformers/LaBSE"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Loaded sentence transformer: {model_name}")
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise
    
    async def generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using sentence-transformers"""
        # Run in thread pool since it's CPU-bound
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, 
            lambda: self.model.encode(texts, convert_to_numpy=True)
        )
        
        # Convert to list of lists
        return embeddings.tolist()
    
    def get_dimension(self) -> int:
        return self.dimension


class ProductEmbeddingGenerator:
    """
    Specialized embedding generator for products
    Creates rich embeddings by combining multiple aspects
    """
    
    def __init__(self, base_generator: EmbeddingGenerator = None):
        if base_generator is None:
            # Default to OpenAI if available
            if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "mock_key_for_testing":
                base_generator = OpenAIEmbeddingGenerator()
            else:
                base_generator = SentenceTransformerEmbeddingGenerator()
        
        self.base_generator = base_generator
        self.cache = {}
    
    async def generate_product_embedding(self, 
                                       product_name: str,
                                       specifications: Dict[str, Any] = None,
                                       category: str = None) -> List[float]:
        """
        Generate rich embedding for a product
        
        Combines:
        - Product name
        - Technical specifications
        - Category information
        """
        # Create cache key
        cache_key = f"{product_name}:{category}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Build comprehensive text representation
        text_parts = [product_name]
        
        # Add category context
        if category:
            text_parts.append(f"Категория: {category}")
        
        # Add specifications
        if specifications:
            spec_text = self._format_specifications(specifications)
            if spec_text:
                text_parts.append(spec_text)
        
        # Combine into single text
        full_text = " | ".join(text_parts)
        
        # Generate embedding
        embeddings = await self.base_generator.generate([full_text])
        embedding = embeddings[0]
        
        # Cache result
        self.cache[cache_key] = embedding
        
        return embedding
    
    async def generate_batch_embeddings(self, 
                                      products: List[Dict[str, Any]]) -> List[List[float]]:
        """Generate embeddings for multiple products efficiently"""
        # Prepare texts
        texts = []
        for product in products:
            text_parts = [product["name"]]
            
            if product.get("category"):
                text_parts.append(f"Категория: {product['category']}")
            
            if product.get("specifications"):
                spec_text = self._format_specifications(product["specifications"])
                if spec_text:
                    text_parts.append(spec_text)
            
            texts.append(" | ".join(text_parts))
        
        # Generate all embeddings at once
        return await self.base_generator.generate(texts)
    
    def _format_specifications(self, specifications: Dict[str, Any]) -> str:
        """Format specifications for embedding"""
        spec_parts = []
        
        for key, value in specifications.items():
            if value and str(value).strip():
                # Clean key name
                clean_key = key.replace("_", " ").title()
                spec_parts.append(f"{clean_key}: {value}")
        
        return " | ".join(spec_parts[:10])  # Limit to top 10 specs
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a search query"""
        # For queries, we might want to expand with synonyms
        expanded_query = self._expand_query(query)
        embeddings = await self.base_generator.generate([expanded_query])
        return embeddings[0]
    
    def _expand_query(self, query: str) -> str:
        """Expand query with relevant terms"""
        # Simple expansion - could be enhanced with synonyms
        expansions = {
            "датчик": "датчик сенсор измеритель преобразователь",
            "круг": "круг пруток стальной металлопрокат",
            "молоток": "молоток инструмент ударный",
            "шина": "шина покрышка резина автомобильная"
        }
        
        query_lower = query.lower()
        for term, expansion in expansions.items():
            if term in query_lower:
                return f"{query} {expansion}"
        
        return query
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.base_generator.get_dimension()


class EmbeddingFactory:
    """Factory for creating embedding generators"""
    
    @staticmethod
    def create(provider: str = None) -> EmbeddingGenerator:
        """
        Create embedding generator
        
        Args:
            provider: "openai", "sentence-transformers", or None (auto-detect)
        """
        if provider is None:
            # Auto-detect
            if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "mock_key_for_testing":
                provider = "openai"
            else:
                provider = "sentence-transformers"
        
        if provider == "openai":
            model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
            return OpenAIEmbeddingGenerator(model)
        elif provider == "sentence-transformers":
            model = os.getenv("SENTENCE_TRANSFORMER_MODEL", "sentence-transformers/LaBSE")
            return SentenceTransformerEmbeddingGenerator(model)
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")
