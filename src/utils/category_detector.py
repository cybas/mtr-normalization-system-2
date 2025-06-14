"""
Smart Category Detector for Mixed Product Classification
"""
import re
from typing import List, Tuple, Dict, Optional
from collections import Counter
import numpy as np
from src.models.models import ProductCategory
from config.config import PRODUCT_CATEGORIES


class CategoryDetector:
    """
    Intelligent product category detection using multiple strategies:
    1. Keyword matching (Russian & English)
    2. Pattern recognition
    3. Manufacturer/brand detection
    4. Embedding similarity (future)
    """
    
    def __init__(self):
        self.categories = PRODUCT_CATEGORIES
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for each category"""
        self.patterns = {}
        
        # Pressure sensors patterns
        self.patterns[ProductCategory.PRESSURE_SENSOR] = [
            re.compile(r'датчик.*давлен', re.IGNORECASE),
            re.compile(r'pressure\s*sensor', re.IGNORECASE),
            re.compile(r'преобразователь.*давлен', re.IGNORECASE),
            re.compile(r'ПД\d+', re.IGNORECASE),  # ОВЕН ПД100И pattern
            re.compile(r'(Endress\+Hauser|ОВЕН|Danfoss|Siemens).*давлен', re.IGNORECASE),
            re.compile(r'(PMP|PMC|PTP|CeraBar|Deltabar)', re.IGNORECASE),  # Model patterns
            re.compile(r'\d+\s*(МПа|MPa|кПа|kPa|бар|bar)', re.IGNORECASE),  # Pressure units
        ]
        
        # Steel circles patterns  
        self.patterns[ProductCategory.STEEL_CIRCLE] = [
            re.compile(r'круг.*сталь', re.IGNORECASE),
            re.compile(r'steel.*circle', re.IGNORECASE),
            re.compile(r'прокат.*круг', re.IGNORECASE),
            re.compile(r'горячекатан.*круг', re.IGNORECASE),
            re.compile(r'ГОСТ\s*2590', re.IGNORECASE),  # Standard for steel circles
            re.compile(r'\d+\s*мм.*сталь', re.IGNORECASE),  # Diameter pattern
            re.compile(r'сталь.*\d+', re.IGNORECASE),  # Steel grade pattern
        ]
        
        # Hammers patterns
        self.patterns[ProductCategory.HAMMER] = [
            re.compile(r'молот', re.IGNORECASE),
            re.compile(r'hammer', re.IGNORECASE),
            re.compile(r'слесарн.*молот', re.IGNORECASE),
            re.compile(r'электромонтаж.*молот', re.IGNORECASE),
            re.compile(r'\d+\s*(кг|kg).*молот', re.IGNORECASE),  # Weight pattern
            re.compile(r'рукоят.*молот', re.IGNORECASE),
            re.compile(r'(Stanley|Gross|Matrix|Sparta)', re.IGNORECASE),  # Hammer brands
        ]
        
        # Tires patterns
        self.patterns[ProductCategory.TIRE] = [
            re.compile(r'шин[аы]', re.IGNORECASE),
            re.compile(r'tire', re.IGNORECASE),
            re.compile(r'резин.*колес', re.IGNORECASE),
            re.compile(r'покрыш', re.IGNORECASE),
            re.compile(r'\d{3}/\d{2}\s*R\d{2}', re.IGNORECASE),  # Tire size pattern
            re.compile(r'(зимн|летн|всесезон)', re.IGNORECASE),  # Season
            re.compile(r'(Nokian|Michelin|Bridgestone|Continental|Кама|BFGoodrich)', re.IGNORECASE),
            re.compile(r'(Hakkapeliitta|Pilot|Turanza)', re.IGNORECASE),  # Model names
        ]
        
    def detect_category(self, product_name: str) -> Tuple[ProductCategory, float]:
        """
        Detect product category with confidence score
        
        Returns:
            Tuple[ProductCategory, float]: Category and confidence (0-1)
        """
        if not product_name:
            return ProductCategory.UNKNOWN, 0.0
            
        # Clean and normalize text
        normalized = self._normalize_text(product_name)
        
        # Score each category
        scores = {}
        for category in ProductCategory:
            if category == ProductCategory.UNKNOWN:
                continue
            scores[category] = self._calculate_category_score(normalized, category)
        
        # Get best match
        if not scores:
            return ProductCategory.UNKNOWN, 0.0
            
        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]
        
        # Threshold check
        if confidence < 0.3:
            return ProductCategory.UNKNOWN, confidence
            
        return best_category, confidence
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching"""
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep important ones
        text = re.sub(r'[^\w\s\-\+/\.\,А-Яа-я]', ' ', text)
        return text.strip()
    
    def _calculate_category_score(self, text: str, category: ProductCategory) -> float:
        """Calculate matching score for a category"""
        score = 0.0
        
        # Pattern matching
        if category in self.patterns:
            pattern_matches = sum(1 for pattern in self.patterns[category] 
                                if pattern.search(text))
            score += pattern_matches * 0.3
        
        # Keyword matching
        if category.value in self.categories:
            keywords = self.categories[category.value].get("keywords", [])
            keyword_matches = sum(1 for keyword in keywords 
                                if keyword.lower() in text.lower())
            score += keyword_matches * 0.2
        
        # Normalize score to 0-1 range
        return min(score, 1.0)
    
    def detect_batch(self, product_names: List[str]) -> List[Tuple[ProductCategory, float]]:
        """Detect categories for a batch of products"""
        return [self.detect_category(name) for name in product_names]
    
    def get_category_distribution(self, products: List[str]) -> Dict[ProductCategory, int]:
        """Get distribution of categories in a product list"""
        categories = [self.detect_category(p)[0] for p in products]
        return Counter(categories)
    
    def suggest_category_keywords(self, product_name: str, category: ProductCategory) -> List[str]:
        """Suggest keywords that would improve categorization"""
        suggestions = []
        
        if category == ProductCategory.UNKNOWN:
            # Analyze what keywords might help
            for cat, config in self.categories.items():
                keywords = config.get("keywords", [])
                for keyword in keywords:
                    if keyword.lower() in product_name.lower():
                        suggestions.append(f"Contains '{keyword}' - might be {cat}")
        
        return suggestions


class SmartCategoryDetector(CategoryDetector):
    """
    Enhanced category detector with learning capabilities
    """
    
    def __init__(self):
        super().__init__()
        self.learned_patterns = {}
        self.misclassified = []
        
    def learn_from_correction(self, product_name: str, 
                            predicted_category: ProductCategory,
                            correct_category: ProductCategory):
        """Learn from misclassification"""
        self.misclassified.append({
            "product": product_name,
            "predicted": predicted_category,
            "correct": correct_category
        })
        
        # Extract patterns from correct classifications
        if correct_category != ProductCategory.UNKNOWN:
            if correct_category not in self.learned_patterns:
                self.learned_patterns[correct_category] = []
            
            # Extract n-grams as patterns
            words = product_name.lower().split()
            for i in range(len(words)):
                for j in range(i+1, min(i+4, len(words)+1)):
                    pattern = " ".join(words[i:j])
                    if len(pattern) > 3:  # Minimum pattern length
                        self.learned_patterns[correct_category].append(pattern)
    
    def _calculate_category_score(self, text: str, category: ProductCategory) -> float:
        """Enhanced scoring with learned patterns"""
        # Base score from parent
        score = super()._calculate_category_score(text, category)
        
        # Add learned pattern score
        if category in self.learned_patterns:
            learned_matches = sum(1 for pattern in self.learned_patterns[category]
                                if pattern in text.lower())
            score += learned_matches * 0.1
        
        return min(score, 1.0)
