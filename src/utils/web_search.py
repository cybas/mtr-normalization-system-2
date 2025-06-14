"""
Web Search Utilities for Product Research
Supports multiple search engines and intelligent query building
"""
import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
import json
import re
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)


class WebSearcher:
    """
    Unified web search interface supporting multiple search providers
    """
    
    def __init__(self, provider: str = "duckduckgo"):
        self.provider = provider
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform web search
        
        Returns:
            List of search results with title, url, snippet
        """
        if self.provider == "duckduckgo":
            return await self._search_duckduckgo(query, num_results)
        elif self.provider == "google":
            return await self._search_google_custom(query, num_results)
        else:
            logger.warning(f"Unknown provider {self.provider}, using DuckDuckGo")
            return await self._search_duckduckgo(query, num_results)
    
    async def _search_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo (no API key required)"""
        try:
            # DuckDuckGo HTML search
            url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"DuckDuckGo search failed: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                results = []
                for result in soup.find_all('div', class_='result', limit=num_results):
                    try:
                        title_elem = result.find('a', class_='result__a')
                        snippet_elem = result.find('a', class_='result__snippet')
                        
                        if title_elem:
                            results.append({
                                "title": title_elem.get_text(strip=True),
                                "url": title_elem.get('href', ''),
                                "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                            })
                    except Exception as e:
                        logger.error(f"Error parsing result: {e}")
                        continue
                
                return results
                
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    async def _search_google_custom(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using Google Custom Search API (requires API key)"""
        # This would require Google API key and Custom Search Engine ID
        # Placeholder implementation
        logger.info(f"Google search placeholder for: {query}")
        return []
    
    async def search_classifikators_ru(self, query: str) -> List[Dict[str, Any]]:
        """
        Specialized search for classifikators.ru OKPD2 codes
        """
        try:
            # Direct search on classifikators.ru
            base_url = "https://classifikators.ru/okpd"
            search_url = f"{base_url}?q={quote_plus(query)}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    logger.error(f"Classifikators search failed: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                results = []
                # Parse OKPD2 codes from the page
                # This is a simplified example - actual parsing would be more complex
                for item in soup.find_all('div', class_='okpd-item', limit=10):
                    code = item.find('span', class_='code')
                    name = item.find('span', class_='name')
                    
                    if code and name:
                        results.append({
                            "code": code.get_text(strip=True),
                            "name": name.get_text(strip=True),
                            "url": f"{base_url}/{code.get_text(strip=True)}"
                        })
                
                return results
                
        except Exception as e:
            logger.error(f"Classifikators search error: {e}")
            return []


class ProductSearchBuilder:
    """
    Intelligent search query builder for product research
    """
    
    @staticmethod
    def build_queries(product_name: str, category: str = None) -> List[str]:
        """
        Build multiple search queries for comprehensive research
        """
        queries = []
        
        # Clean product name
        cleaned_name = ProductSearchBuilder._clean_product_name(product_name)
        
        # Basic product search
        queries.append(cleaned_name)
        
        # Extract potential model/article
        model_match = re.search(r'[A-Z0-9]{3,}[-A-Z0-9]*', product_name)
        if model_match:
            model = model_match.group()
            queries.append(f"{model} технические характеристики")
            queries.append(f"{model} specifications datasheet")
        
        # Extract manufacturer
        manufacturers = ProductSearchBuilder._extract_manufacturer(product_name)
        for manufacturer in manufacturers:
            queries.append(f"{manufacturer} {cleaned_name}")
            queries.append(f'site:{manufacturer.lower()}.com {cleaned_name}')
        
        # Category-specific queries
        if category:
            if "sensor" in category.lower():
                queries.append(f"{cleaned_name} измерительный диапазон точность")
                queries.append(f"{cleaned_name} pressure range accuracy output")
            elif "steel" in category.lower():
                queries.append(f"{cleaned_name} ГОСТ марка стали диаметр")
                queries.append(f"{cleaned_name} steel grade diameter standard")
            elif "hammer" in category.lower():
                queries.append(f"{cleaned_name} вес длина рукоятка")
                queries.append(f"{cleaned_name} weight length handle material")
            elif "tire" in category.lower():
                queries.append(f"{cleaned_name} размер индекс скорости нагрузки")
                queries.append(f"{cleaned_name} size speed load index")
        
        # Technical documentation queries
        queries.append(f'"{cleaned_name}" filetype:pdf')
        queries.append(f"{cleaned_name} каталог продукции")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        
        return unique_queries[:5]  # Limit to top 5 queries
    
    @staticmethod
    def _clean_product_name(product_name: str) -> str:
        """Clean product name for search"""
        # Remove extra spaces
        cleaned = re.sub(r'\s+', ' ', product_name)
        
        # Remove special characters but keep important ones
        cleaned = re.sub(r'[^\w\s\-\+/\.\,А-Яа-я]', ' ', cleaned)
        
        # Remove common stop words
        stop_words = ['для', 'with', 'and', 'или', 'the']
        words = cleaned.split()
        cleaned_words = [w for w in words if w.lower() not in stop_words]
        
        return ' '.join(cleaned_words).strip()
    
    @staticmethod
    def _extract_manufacturer(product_name: str) -> List[str]:
        """Extract potential manufacturer names"""
        manufacturers = []
        
        # Known manufacturer patterns
        known_brands = [
            "Endress+Hauser", "ОВЕН", "Danfoss", "Siemens", "ABB",
            "Schneider", "Honeywell", "Yokogawa", "Emerson", "Rosemount",
            "SKF", "FAG", "Timken", "NSK", "NTN",
            "Stanley", "Bosch", "Makita", "DeWalt", "Gross",
            "Michelin", "Bridgestone", "Continental", "Nokian", "Goodyear"
        ]
        
        # Check for known brands
        name_upper = product_name.upper()
        for brand in known_brands:
            if brand.upper() in name_upper:
                manufacturers.append(brand)
        
        # Extract potential brand from beginning of name
        words = product_name.split()
        if words and words[0].isupper() and len(words[0]) > 2:
            potential_brand = words[0]
            if potential_brand not in manufacturers:
                manufacturers.append(potential_brand)
        
        return manufacturers


class SmartProductSearcher:
    """
    Advanced product searcher with caching and intelligent result processing
    """
    
    def __init__(self):
        self.search_cache = {}
        self.searcher = None
        
    async def search_product_info(self, 
                                product_name: str,
                                category: str = None,
                                use_cache: bool = True) -> Dict[str, Any]:
        """
        Comprehensive product search with intelligent processing
        """
        # Check cache
        cache_key = f"{product_name}:{category}"
        if use_cache and cache_key in self.search_cache:
            logger.info(f"Using cached results for {product_name}")
            return self.search_cache[cache_key]
        
        # Build search queries
        queries = ProductSearchBuilder.build_queries(product_name, category)
        
        # Perform searches
        all_results = []
        async with WebSearcher() as searcher:
            for query in queries:
                logger.info(f"Searching: {query}")
                results = await searcher.search(query, num_results=3)
                all_results.extend(results)
                
                # Rate limiting
                await asyncio.sleep(0.5)
        
        # Process and structure results
        processed_results = self._process_search_results(all_results, product_name)
        
        # Cache results
        if use_cache:
            self.search_cache[cache_key] = processed_results
        
        return processed_results
    
    def _process_search_results(self, 
                              results: List[Dict[str, Any]], 
                              product_name: str) -> Dict[str, Any]:
        """Process and structure search results"""
        processed = {
            "product_name": product_name,
            "sources": [],
            "extracted_info": {
                "specifications": {},
                "manufacturer": None,
                "model": None,
                "standards": []
            },
            "confidence": 0.0
        }
        
        # Deduplicate and score results
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                
                # Score relevance
                title = result.get("title", "").lower()
                snippet = result.get("snippet", "").lower()
                product_lower = product_name.lower()
                
                score = 0
                if any(word in title for word in product_lower.split()):
                    score += 2
                if any(word in snippet for word in product_lower.split()):
                    score += 1
                
                result["relevance_score"] = score
                unique_results.append(result)
        
        # Sort by relevance
        unique_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Take top results
        processed["sources"] = unique_results[:5]
        
        # Extract information from snippets
        for result in unique_results[:3]:
            self._extract_specs_from_text(
                result.get("snippet", ""), 
                processed["extracted_info"]
            )
        
        # Calculate confidence
        if unique_results:
            avg_score = sum(r["relevance_score"] for r in unique_results[:3]) / 3
            processed["confidence"] = min(avg_score / 3, 1.0)
        
        return processed
    
    def _extract_specs_from_text(self, text: str, info_dict: Dict[str, Any]):
        """Extract specifications from text snippet"""
        # Extract measurements with units
        measurements = re.findall(
            r'(\d+(?:\.\d+)?)\s*(мм|mm|кг|kg|МПа|MPa|bar|бар|°C|В|V|mA|мА)', 
            text, 
            re.IGNORECASE
        )
        
        for value, unit in measurements:
            unit_lower = unit.lower()
            if unit_lower in ["мм", "mm"]:
                info_dict["specifications"]["dimension_mm"] = value
            elif unit_lower in ["кг", "kg"]:
                info_dict["specifications"]["weight_kg"] = value
            elif unit_lower in ["мпа", "mpa", "bar", "бар"]:
                info_dict["specifications"]["pressure"] = f"{value} {unit}"
        
        # Extract standards
        standards = re.findall(r'(ГОСТ|GOST|DIN|ISO)\s*[\d\-\.]+', text, re.IGNORECASE)
        info_dict["standards"].extend(standards)
