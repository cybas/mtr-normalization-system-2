"""
Vector Database Integration for Product Embeddings
Supports Pinecone and ChromaDB for flexibility
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import numpy as np
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector stores"""
    
    @abstractmethod
    async def upsert(self, embeddings: List[Tuple[str, List[float], Dict[str, Any]]]):
        """Insert or update embeddings"""
        pass
    
    @abstractmethod
    async def query(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Query similar embeddings"""
        pass
    
    @abstractmethod
    async def delete(self, ids: List[str]):
        """Delete embeddings by ID"""
        pass


class PineconeStore(VectorStore):
    """Pinecone vector database implementation"""
    
    def __init__(self, index_name: str, dimension: int = 3072):
        self.index_name = index_name
        self.dimension = dimension
        self.index = None
        
        try:
            import pinecone
            
            # Initialize Pinecone
            pinecone.init(
                api_key=os.getenv("PINECONE_API_KEY"),
                environment=os.getenv("PINECONE_ENV", "us-east-1")
            )
            
            # Create index if it doesn't exist
            if index_name not in pinecone.list_indexes():
                logger.info(f"Creating Pinecone index: {index_name}")
                pinecone.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric="cosine"
                )
            
            self.index = pinecone.Index(index_name)
            logger.info(f"Connected to Pinecone index: {index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
    
    async def upsert(self, embeddings: List[Tuple[str, List[float], Dict[str, Any]]]):
        """Insert or update embeddings in Pinecone"""
        if not self.index:
            raise ValueError("Pinecone index not initialized")
        
        # Prepare vectors for upsert
        vectors = []
        for id_, embedding, metadata in embeddings:
            # Ensure metadata is JSON serializable
            clean_metadata = self._clean_metadata(metadata)
            vectors.append((id_, embedding, clean_metadata))
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)
        
        logger.info(f"Upserted {len(embeddings)} vectors to Pinecone")
    
    async def query(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Query similar products from Pinecone"""
        if not self.index:
            raise ValueError("Pinecone index not initialized")
        
        results = self.index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        # Format results
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata
            })
        
        return formatted_results
    
    async def delete(self, ids: List[str]):
        """Delete vectors by ID"""
        if not self.index:
            raise ValueError("Pinecone index not initialized")
        
        self.index.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} vectors from Pinecone")
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Clean metadata for Pinecone storage"""
        clean = {}
        for key, value in metadata.items():
            # Convert datetime to string
            if isinstance(value, datetime):
                clean[key] = value.isoformat()
            # Convert numpy types
            elif isinstance(value, np.ndarray):
                clean[key] = value.tolist()
            elif isinstance(value, (np.integer, np.floating)):
                clean[key] = float(value)
            # Keep simple types
            elif isinstance(value, (str, int, float, bool, list)):
                clean[key] = value
            # Convert dict to string
            elif isinstance(value, dict):
                clean[key] = json.dumps(value, ensure_ascii=False)
            else:
                clean[key] = str(value)
        return clean


class ChromaStore(VectorStore):
    """ChromaDB vector database implementation (local alternative)"""
    
    def __init__(self, collection_name: str = "mtr_products", 
                 persist_directory: str = "./data/chroma"):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        
        try:
            import chromadb
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=persist_directory)
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"Connected to ChromaDB collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    async def upsert(self, embeddings: List[Tuple[str, List[float], Dict[str, Any]]]):
        """Insert or update embeddings in ChromaDB"""
        if not self.collection:
            raise ValueError("ChromaDB collection not initialized")
        
        # Separate components
        ids = [e[0] for e in embeddings]
        vectors = [e[1] for e in embeddings]
        metadatas = [self._clean_metadata(e[2]) for e in embeddings]
        
        # Upsert to collection
        self.collection.upsert(
            ids=ids,
            embeddings=vectors,
            metadatas=metadatas
        )
        
        logger.info(f"Upserted {len(embeddings)} vectors to ChromaDB")
    
    async def query(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Query similar products from ChromaDB"""
        if not self.collection:
            raise ValueError("ChromaDB collection not initialized")
        
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "score": 1 - results['distances'][0][i],  # Convert distance to similarity
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {}
                })
        
        return formatted_results
    
    async def delete(self, ids: List[str]):
        """Delete vectors by ID"""
        if not self.collection:
            raise ValueError("ChromaDB collection not initialized")
        
        self.collection.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} vectors from ChromaDB")
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Clean metadata for ChromaDB storage"""
        clean = {}
        for key, value in metadata.items():
            # ChromaDB is more flexible with types
            if isinstance(value, datetime):
                clean[key] = value.isoformat()
            elif isinstance(value, (np.ndarray, list)):
                clean[key] = str(value)
            elif isinstance(value, dict):
                clean[key] = json.dumps(value, ensure_ascii=False)
            else:
                clean[key] = str(value)
        return clean


class VectorStoreFactory:
    """Factory for creating vector stores"""
    
    @staticmethod
    def create(provider: str = None) -> VectorStore:
        """
        Create a vector store instance
        
        Args:
            provider: "pinecone", "chroma", or None (auto-detect)
        """
        if provider is None:
            # Auto-detect based on available API keys
            if os.getenv("PINECONE_API_KEY") and os.getenv("PINECONE_API_KEY") != "mock_key_for_testing":
                provider = "pinecone"
            else:
                provider = "chroma"
        
        if provider == "pinecone":
            return PineconeStore(
                index_name=os.getenv("PINECONE_INDEX_NAME", "mtr-products")
            )
        elif provider == "chroma":
            return ChromaStore(
                persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
            )
        else:
            raise ValueError(f"Unknown vector store provider: {provider}")


class ProductEmbeddingManager:
    """Manages product embeddings and similarity search"""
    
    def __init__(self, vector_store: VectorStore = None):
        self.vector_store = vector_store or VectorStoreFactory.create()
        self.embedding_cache = {}
        
    async def store_product(self, product_id: str, 
                          product_name: str,
                          embedding: List[float],
                          metadata: Dict[str, Any]):
        """Store product embedding"""
        # Add timestamp
        metadata["indexed_at"] = datetime.now().isoformat()
        metadata["product_name"] = product_name
        
        await self.vector_store.upsert([(product_id, embedding, metadata)])
        
        # Cache embedding
        self.embedding_cache[product_id] = embedding
    
    async def find_similar_products(self, product_name: str,
                                  embedding: List[float],
                                  top_k: int = 5) -> List[Dict[str, Any]]:
        """Find similar products"""
        results = await self.vector_store.query(embedding, top_k)
        
        # Filter out exact matches
        filtered = []
        for result in results:
            if result["metadata"].get("product_name") != product_name:
                filtered.append(result)
        
        return filtered
    
    async def batch_store(self, products: List[Dict[str, Any]]):
        """Store multiple products efficiently"""
        embeddings_data = []
        
        for product in products:
            product_id = product["id"]
            embedding = product["embedding"]
            metadata = product.get("metadata", {})
            metadata["product_name"] = product["name"]
            
            embeddings_data.append((product_id, embedding, metadata))
        
        await self.vector_store.upsert(embeddings_data)
        logger.info(f"Stored {len(products)} product embeddings")
