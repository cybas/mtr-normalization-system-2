"""
Product Research Agent
Researches product specifications using web search and AI analysis
"""
import json
import re
from typing import Dict, Any, List, Optional
import logging

from src.agents.base_agent import BaseAgent
from src.models.models import Product, ResearchResult, ProductCategory
from config.config import PRODUCT_CATEGORIES

logger = logging.getLogger(__name__)


class ProductResearchAgent(BaseAgent):
    """
    AI Agent 1: Product Researcher
    - Analyzes product names
    - Searches for manufacturer info and specifications
    - Extracts technical characteristics
    """
    
    def __init__(self):
        super().__init__("ProductResearchAgent")
        self.research_prompts = self._load_research_prompts()
        
    def _load_research_prompts(self) -> Dict[str, str]:
        """Load category-specific research prompts"""
        return {
            ProductCategory.PRESSURE_SENSOR: """
            Research this pressure sensor and extract specifications:
            Product: {product_name}
            
            Find and extract:
            1. Manufacturer/Brand
            2. Model/Article number
            3. Measurement type (absolute, gauge, differential)
            4. Measurement range
            5. Accuracy class
            6. Output signal type
            7. Operating temperature range
            8. Protection class (IP rating)
            9. Explosion protection certification
            10. Connection type
            11. Material
            12. Dimensions
            13. Weight
            
            Return structured JSON with all available specifications.
            """,
            
            ProductCategory.STEEL_CIRCLE: """
            Research this steel product and extract specifications:
            Product: {product_name}
            
            Find and extract:
            1. Steel grade/mark
            2. Diameter (mm)
            3. Length
            4. Surface quality class
            5. Rolling accuracy
            6. Hardness
            7. Manufacturing standard (GOST)
            8. Weight per meter
            9. Chemical composition if available
            10. Mechanical properties
            
            Return structured JSON with all available specifications.
            """,
            
            ProductCategory.HAMMER: """
            Research this hammer and extract specifications:
            Product: {product_name}
            
            Find and extract:
            1. Manufacturer/Brand
            2. Hammer type (sledge, claw, ball-peen, etc.)
            3. Head weight (kg)
            4. Total length (mm)
            5. Handle material
            6. Head material
            7. Model/Article number
            8. Standards compliance
            9. Special features
            
            Return structured JSON with all available specifications.
            """,
            
            ProductCategory.TIRE: """
            Research this tire and extract specifications:
            Product: {product_name}
            
            Find and extract:
            1. Manufacturer/Brand
            2. Model name
            3. Size (width/profile/diameter)
            4. Season type (summer/winter/all-season)
            5. Speed index
            6. Load index
            7. Tread pattern
            8. Studs (yes/no)
            9. Run-flat capability
            10. Fuel efficiency rating
            11. Wet grip rating
            12. Noise level
            
            Return structured JSON with all available specifications.
            """
        }
    
    async def process(self, context: Dict[str, Any]) -> ResearchResult:
        """Research product and extract specifications"""
        product = context["product"]
        category = context.get("category", ProductCategory.UNKNOWN)
        
        logger.info(f"Researching product: {product.original_name}")
        
        # Step 1: Extract key information from product name
        extracted_info = await self._extract_from_name(product.original_name)
        
        # Step 2: Search for additional information
        search_results = await self._search_product_info(product.original_name, extracted_info)
        
        # Step 3: Analyze and structure information
        research_result = await self._analyze_and_structure(
            product, category, extracted_info, search_results
        )
        
        return research_result
    
    async def _extract_from_name(self, product_name: str) -> Dict[str, Any]:
        """Extract information directly from product name"""
        prompt = f"""
        Analyze this product name and extract any specifications or identifiers:
        "{product_name}"
        
        Extract:
        - Brand/Manufacturer
        - Model/Article
        - Key specifications (size, capacity, etc.)
        - Standards mentioned (GOST, DIN, etc.)
        
        Return as JSON.
        """
        
        messages = [
            {"role": "system", "content": "You are a technical product analyst."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._call_llm(messages)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Failed to extract from name: {str(e)}")
            return {}
    
    async def _search_product_info(self, product_name: str, 
                                 extracted_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for product information"""
        # Build targeted search queries
        queries = []
        
        # Base query
        queries.append(product_name)
        
        # Add manufacturer-specific query if found
        if "manufacturer" in extracted_info:
            queries.append(f"{extracted_info['manufacturer']} {extracted_info.get('model', '')}")
        
        # Add specification query
        queries.append(f"{product_name} технические характеристики specifications")
        
        # Perform searches
        all_results = []
        for query in queries[:3]:  # Limit to 3 searches
            results = await self._web_search(query, num_results=3)
            all_results.extend(results)
        
        return all_results
    
    async def _analyze_and_structure(self, product: Product,
                                    category: ProductCategory,
                                    extracted_info: Dict[str, Any],
                                    search_results: List[Dict[str, Any]]) -> ResearchResult:
        """Analyze all information and structure into ResearchResult"""
        
        # Get category-specific prompt
        prompt_template = self.research_prompts.get(
            category, 
            self.research_prompts[ProductCategory.PRESSURE_SENSOR]
        )
        
        # Build context
        search_context = "\n".join([
            f"Source: {r['url']}\n{r['snippet']}" 
            for r in search_results[:5]
        ])
        
        prompt = f"""
        {prompt_template.format(product_name=product.original_name)}
        
        Information extracted from name: {json.dumps(extracted_info, ensure_ascii=False)}
        
        Search results:
        {search_context}
        
        Provide comprehensive specifications in JSON format.
        If information is not found, use null values.
        Include confidence score (0-1) for the overall result.
        """
        
        messages = [
            {"role": "system", "content": "You are a technical product specification expert."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._call_llm(messages, temperature=0.1)
            spec_data = json.loads(response)
            
            # Create ResearchResult
            result = ResearchResult(
                product_name=product.original_name,
                manufacturer=spec_data.get("manufacturer"),
                model=spec_data.get("model"),
                specifications=spec_data.get("specifications", {}),
                sources=[r["url"] for r in search_results[:3]],
                confidence=spec_data.get("confidence", 0.7),
                raw_data=spec_data
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze product: {str(e)}")
            
            # Return basic result
            return ResearchResult(
                product_name=product.original_name,
                manufacturer=extracted_info.get("manufacturer"),
                model=extracted_info.get("model"),
                specifications=extracted_info,
                sources=[],
                confidence=0.3
            )
