"""
OKPD2 Classifier Agent
Finds and validates OKPD2 classification codes
"""
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import logging
import aiohttp
from bs4 import BeautifulSoup

from src.agents.base_agent import BaseAgent
from src.models.models import Product, OKPD2Result, ProductCategory
from config.config import OKPD2_CONFIG, PRODUCT_CATEGORIES

logger = logging.getLogger(__name__)


class OKPD2ClassifierAgent(BaseAgent):
    """
    AI Agent 2: OKPD2 Classifier
    - Searches classifikators.ru for OKPD2 codes
    - Finds maximum available classification level
    - Validates codes against product type
    """
    
    def __init__(self):
        super().__init__("OKPD2ClassifierAgent")
        self.base_url = OKPD2_CONFIG["base_url"]
        self.okpd2_cache = {}  # Cache for codes
        
    async def process(self, context: Dict[str, Any]) -> OKPD2Result:
        """Find and validate OKPD2 code for product"""
        product = context["product"]
        research_result = context.get("research_result")
        category = context.get("category", ProductCategory.UNKNOWN)
        
        logger.info(f"Classifying OKPD2 for: {product.original_name}")
        
        # Step 1: Generate search terms
        search_terms = self._generate_search_terms(product, research_result, category)
        
        # Step 2: Search for OKPD2 codes
        candidate_codes = await self._search_okpd2_codes(search_terms)
        
        # Step 3: Validate and select best code
        best_code = await self._select_best_code(
            candidate_codes, product, category, research_result
        )
        
        return best_code
    
    def _generate_search_terms(self, product: Product, 
                             research_result: Optional[Dict], 
                             category: ProductCategory) -> List[str]:
        """Generate search terms for OKPD2 lookup"""
        terms = []
        
        # Category-based terms
        if category in PRODUCT_CATEGORIES:
            cat_config = PRODUCT_CATEGORIES[category.value]
            # Add category keywords
            terms.extend(cat_config.get("keywords", []))
        
        # Product name analysis
        name_parts = product.original_name.split()
        
        # Extract key product terms
        key_terms = []
        for part in name_parts:
            # Skip common words and numbers
            if len(part) > 3 and not part.isdigit() and part.lower() not in [
                "для", "with", "and", "или", "the", "гост", "din"
            ]:
                key_terms.append(part)
        
        terms.extend(key_terms[:3])  # Top 3 key terms
        
        # Add manufacturer/model if available
        if research_result:
            if research_result.get("manufacturer"):
                terms.append(research_result["manufacturer"])
            if research_result.get("product_type"):
                terms.append(research_result["product_type"])
        
        # Category-specific terms
        category_terms = {
            ProductCategory.PRESSURE_SENSOR: ["датчик давления", "преобразователь давления"],
            ProductCategory.STEEL_CIRCLE: ["круг стальной", "прокат круглый"],
            ProductCategory.HAMMER: ["молоток", "инструмент ударный"],
            ProductCategory.TIRE: ["шина", "покрышка автомобильная"]
        }
        
        if category in category_terms:
            terms.extend(category_terms[category])
        
        # Remove duplicates and return
        return list(dict.fromkeys(terms))[:5]  # Top 5 unique terms
    
    async def _search_okpd2_codes(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Search for OKPD2 codes using multiple strategies"""
        all_candidates = []
        
        for term in search_terms:
            # Check cache first
            if term in self.okpd2_cache:
                all_candidates.extend(self.okpd2_cache[term])
                continue
            
            # Search using web scraping (placeholder - implement actual scraping)
            candidates = await self._scrape_classifikators(term)
            
            # Cache results
            self.okpd2_cache[term] = candidates
            all_candidates.extend(candidates)
        
        # Also use LLM knowledge
        llm_suggestions = await self._get_llm_suggestions(search_terms)
        all_candidates.extend(llm_suggestions)
        
        # Deduplicate by code
        seen_codes = set()
        unique_candidates = []
        for candidate in all_candidates:
            if candidate["code"] not in seen_codes:
                seen_codes.add(candidate["code"])
                unique_candidates.append(candidate)
        
        return unique_candidates
    
    async def _scrape_classifikators(self, search_term: str) -> List[Dict[str, Any]]:
        """Scrape classifikators.ru for OKPD2 codes"""
        # This is a placeholder - actual implementation would scrape the website
        # For now, return mock data
        
        # In production, this would:
        # 1. Make HTTP request to classifikators.ru/okpd
        # 2. Parse HTML with BeautifulSoup
        # 3. Extract code hierarchy
        # 4. Return structured results
        
        mock_codes = {
            "датчик": [
                {"code": "26.51.52.110", "name": "Датчики давления", "level": 4},
                {"code": "26.51.52", "name": "Приборы для измерения давления", "level": 3}
            ],
            "круг": [
                {"code": "24.10.75.111", "name": "Прокат круглый", "level": 4},
                {"code": "24.10.75", "name": "Прокат стальной", "level": 3}
            ],
            "молоток": [
                {"code": "25.73.30.123", "name": "Молотки слесарные", "level": 4},
                {"code": "25.73.30", "name": "Инструмент ручной", "level": 3}
            ],
            "шина": [
                {"code": "22.11.11.000", "name": "Шины для легковых автомобилей", "level": 4},
                {"code": "22.11.11", "name": "Шины и покрышки", "level": 3}
            ]
        }
        
        # Find matching mock codes
        for key, codes in mock_codes.items():
            if key in search_term.lower():
                return codes
        
        return []
    
    async def _get_llm_suggestions(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Get OKPD2 suggestions from LLM"""
        prompt = f"""
        Find the most specific OKPD2 classification codes for these product terms:
        {', '.join(search_terms)}
        
        OKPD2 is the Russian classification system for products by economic activity.
        
        Provide:
        1. The most specific code available (maximum depth)
        2. Parent codes in the hierarchy
        3. Code descriptions in Russian
        
        Return as JSON array with: code, name, level (1-4 where 4 is most specific)
        """
        
        messages = [
            {"role": "system", "content": "You are an expert in Russian OKPD2 classification."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._call_llm(messages, temperature=0.1)
            suggestions = json.loads(response)
            return suggestions
        except Exception as e:
            logger.error(f"LLM OKPD2 suggestions failed: {str(e)}")
            return []
    
    async def _select_best_code(self, candidates: List[Dict[str, Any]],
                               product: Product,
                               category: ProductCategory,
                               research_result: Optional[Dict]) -> OKPD2Result:
        """Select the best OKPD2 code from candidates"""
        if not candidates:
            # Return default based on category
            if category in PRODUCT_CATEGORIES:
                default_code = PRODUCT_CATEGORIES[category.value].get("okpd2_prefix", "00.00.00")
                return OKPD2Result(
                    code=default_code,
                    name=f"Default classification for {category.value}",
                    level=2,
                    confidence=0.3
                )
            else:
                return OKPD2Result(
                    code="00.00.00",
                    name="Unclassified product",
                    level=1,
                    confidence=0.1
                )
        
        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            score = self._score_candidate(candidate, product, category, research_result)
            scored_candidates.append((score, candidate))
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Get best candidate
        best_score, best_candidate = scored_candidates[0]
        
        # Create result
        result = OKPD2Result(
            code=best_candidate["code"],
            name=best_candidate["name"],
            level=best_candidate.get("level", self._get_code_level(best_candidate["code"])),
            parent_code=self._get_parent_code(best_candidate["code"]),
            confidence=min(best_score, 1.0),
            alternative_codes=[
                {"code": c["code"], "name": c["name"], "score": s}
                for s, c in scored_candidates[1:4]  # Top 3 alternatives
            ]
        )
        
        return result
    
    def _score_candidate(self, candidate: Dict[str, Any],
                        product: Product,
                        category: ProductCategory,
                        research_result: Optional[Dict]) -> float:
        """Score an OKPD2 candidate"""
        score = 0.0
        
        # Level score - prefer more specific codes
        level = candidate.get("level", self._get_code_level(candidate["code"]))
        score += level * 0.2  # Max 0.8 for level 4
        
        # Category match score
        if category in PRODUCT_CATEGORIES:
            expected_prefix = PRODUCT_CATEGORIES[category.value].get("okpd2_prefix", "")
            if candidate["code"].startswith(expected_prefix):
                score += 0.3
        
        # Name relevance score
        name_lower = candidate["name"].lower()
        product_lower = product.original_name.lower()
        
        # Check for keyword matches
        matches = sum(1 for word in product_lower.split() 
                     if len(word) > 3 and word in name_lower)
        score += min(matches * 0.1, 0.3)
        
        # Research result alignment
        if research_result and research_result.get("product_type"):
            if research_result["product_type"].lower() in name_lower:
                score += 0.2
        
        return score
    
    def _get_code_level(self, code: str) -> int:
        """Determine OKPD2 code level from format"""
        parts = code.split(".")
        if len(parts) >= 3 and parts[2] != "00":
            if len(parts) == 4:
                return 4
            return 3
        elif len(parts) >= 2 and parts[1] != "00":
            return 2
        return 1
    
    def _get_parent_code(self, code: str) -> Optional[str]:
        """Get parent OKPD2 code"""
        parts = code.split(".")
        if len(parts) > 1:
            if len(parts) == 4:
                return ".".join(parts[:3])
            elif len(parts) == 3:
                return ".".join(parts[:2])
            elif len(parts) == 2:
                return parts[0]
        return None
