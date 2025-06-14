"""
Base Agent Class for MTR Normalization
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import aiohttp
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from config.config import API_CONFIG

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, name: str):
        self.name = name
        self.api_key = API_CONFIG["openai"]["api_key"]
        self.model = API_CONFIG["openai"]["model"]
        self.temperature = API_CONFIG["openai"]["temperature"]
        self.max_tokens = API_CONFIG["openai"]["max_tokens"]
        
        # Initialize OpenAI client
        openai.api_key = self.api_key
        
    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the context and return results"""
        pass
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _call_llm(self, messages: List[Dict[str, str]], 
                       temperature: Optional[float] = None) -> str:
        """Call OpenAI API with retry logic"""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"{self.name} - LLM call failed: {str(e)}")
            raise
    
    async def _web_search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Perform web search (placeholder - implement with actual search API)"""
        # This would be implemented with Google Custom Search, Bing, or Serper API
        logger.info(f"{self.name} - Searching: {query}")
        
        # Placeholder results
        return [
            {
                "title": f"Result for {query}",
                "url": f"https://example.com/{query.replace(' ', '-')}",
                "snippet": f"Information about {query}..."
            }
        ]
    
    def _build_prompt(self, template: str, **kwargs) -> str:
        """Build prompt from template"""
        return template.format(**kwargs)
