"""
Main MTR Processor
Orchestrates the entire normalization workflow
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import pandas as pd

from src.models.models import (
    Product, ProductCategory, ProcessingStatus, 
    ProcessingBatch, ValidationResult
)
from src.agents.research_agent import ProductResearchAgent
from src.agents.okpd2_agent import OKPD2ClassifierAgent
from src.agents.validation_agent import QualityValidationAgent
from src.utils.excel_parser import ExcelParser
from src.utils.category_detector import SmartCategoryDetector
from config.config import PROCESSING_CONFIG, COMPLIANCE_RULES

logger = logging.getLogger(__name__)


class MTRProcessor:
    """
    Main processor that orchestrates the MTR normalization workflow
    """
    
    def __init__(self):
        # Initialize components
        self.parser = ExcelParser()
        self.category_detector = SmartCategoryDetector()
        
        # Initialize agents
        self.research_agent = ProductResearchAgent()
        self.okpd2_agent = OKPD2ClassifierAgent()
        self.validation_agent = QualityValidationAgent()
        
        # Processing configuration
        self.batch_size = PROCESSING_CONFIG["batch_size"]
        self.max_retries = PROCESSING_CONFIG["max_retries"]
        self.parallel_workers = PROCESSING_CONFIG["parallel_workers"]
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "rejected": 0,
            "failed": 0,
            "processing_time": 0
        }
    
    async def process_file(self, file_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Process a single Excel file
        
        Args:
            file_path: Path to input Excel file
            output_dir: Directory for output files
            
        Returns:
            Processing results and statistics
        """
        start_time = datetime.now()
        logger.info(f"Starting processing of {file_path}")
        
        try:
            # Parse Excel file
            products = self.parser.parse_file(file_path)
            logger.info(f"Parsed {len(products)} products")
            
            # Group by category for efficient processing
            categorized = self._categorize_products(products)
            
            # Process each category
            all_results = []
            for category, category_products in categorized.items():
                logger.info(f"Processing {len(category_products)} {category.value} products")
                
                # Create batches
                batches = self._create_batches(category_products, category)
                
                # Process batches
                for batch in batches:
                    batch_results = await self._process_batch(batch)
                    all_results.extend(batch_results)
            
            # Generate output files
            output_path = await self._generate_output(
                all_results, file_path, output_dir
            )
            
            # Calculate statistics
            end_time = datetime.now()
            self.stats["processing_time"] = (end_time - start_time).total_seconds()
            self.stats["total_processed"] = len(all_results)
            self.stats["successful"] = sum(1 for p in all_results 
                                         if p.status == ProcessingStatus.COMPLETED)
            self.stats["rejected"] = sum(1 for p in all_results 
                                       if p.status == ProcessingStatus.REJECTED)
            self.stats["failed"] = sum(1 for p in all_results 
                                     if p.status == ProcessingStatus.FAILED)
            
            logger.info(f"Processing completed. Stats: {self.stats}")
            
            return {
                "status": "success",
                "output_file": str(output_path),
                "statistics": self.stats,
                "products": all_results
            }
            
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "statistics": self.stats
            }
    
    def _categorize_products(self, products: List[Product]) -> Dict[ProductCategory, List[Product]]:
        """Categorize products using the smart detector"""
        categorized = {}
        
        for product in products:
            # Detect category if not already set
            if product.category == ProductCategory.UNKNOWN:
                category, confidence = self.category_detector.detect_category(
                    product.original_name
                )
                product.category = category
                product.confidence_score = confidence
            
            # Group by category
            if product.category not in categorized:
                categorized[product.category] = []
            categorized[product.category].append(product)
        
        return categorized
    
    def _create_batches(self, products: List[Product], 
                       category: ProductCategory) -> List[ProcessingBatch]:
        """Create processing batches"""
        batches = []
        
        for i in range(0, len(products), self.batch_size):
            batch_products = products[i:i + self.batch_size]
            
            batch = ProcessingBatch(
                batch_id=f"{category.value}_{i//self.batch_size}",
                products=batch_products,
                category=category,
                total_count=len(batch_products)
            )
            batches.append(batch)
        
        return batches
    
    async def _process_batch(self, batch: ProcessingBatch) -> List[Product]:
        """Process a batch of products"""
        batch.start_time = datetime.now()
        processed_products = []
        
        # Process products in parallel (with semaphore to limit concurrency)
        semaphore = asyncio.Semaphore(self.parallel_workers)
        
        async def process_with_semaphore(product):
            async with semaphore:
                return await self._process_single_product(product, batch.category)
        
        # Process all products in batch
        tasks = [process_with_semaphore(product) for product in batch.products]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        for product, result in zip(batch.products, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {product.internal_code}: {str(result)}")
                product.status = ProcessingStatus.FAILED
                product.error_message = str(result)
                batch.failed_count += 1
            else:
                product = result
                batch.processed_count += 1
            
            processed_products.append(product)
        
        batch.end_time = datetime.now()
        return processed_products
    
    async def _process_single_product(self, product: Product, 
                                    category: ProductCategory) -> Product:
        """Process a single product through all agents"""
        try:
            product.status = ProcessingStatus.PROCESSING
            product.processing_timestamp = datetime.now()
            
            # Step 1: Research product
            research_context = {
                "product": product,
                "category": category
            }
            research_result = await self.research_agent.process(research_context)
            
            # Step 2: Find OKPD2 code
            okpd2_context = {
                "product": product,
                "category": category,
                "research_result": research_result.__dict__ if research_result else None
            }
            okpd2_result = await self.okpd2_agent.process(okpd2_context)
            
            # Step 3: Validate quality
            validation_context = {
                "product": product,
                "category": category,
                "research_result": research_result.__dict__ if research_result else None,
                "okpd2_result": okpd2_result.__dict__ if okpd2_result else None
            }
            validation_result = await self.validation_agent.process(validation_context)
            
            # Update product with results
            if research_result:
                product.specifications = research_result.specifications
                if research_result.manufacturer:
                    product.specifications["manufacturer"] = research_result.manufacturer
                if research_result.model:
                    product.specifications["model"] = research_result.model
            
            if okpd2_result:
                product.okpd2_code = okpd2_result.code
            
            # Set normalized unit based on category
            product.normalized_unit = self._get_normalized_unit(product, category)
            
            # Handle validation results
            if validation_result.is_valid:
                product.status = ProcessingStatus.COMPLETED
                product.comment = "Успешно нормализовано"
            else:
                product.status = ProcessingStatus.REJECTED
                product.comment = validation_result.rejection_reason
                product.error_message = "; ".join(validation_result.issues)
            
            return product
            
        except Exception as e:
            logger.error(f"Error processing product {product.internal_code}: {str(e)}")
            product.status = ProcessingStatus.FAILED
            product.error_message = str(e)
            return product
    
    def _get_normalized_unit(self, product: Product, 
                           category: ProductCategory) -> str:
        """Get normalized unit for product"""
        # Get valid units for category
        unit_validation = COMPLIANCE_RULES["unit_validation"]
        
        # Map category to unit key
        unit_keys = {
            ProductCategory.PRESSURE_SENSOR: "датчик",
            ProductCategory.STEEL_CIRCLE: "круг",
            ProductCategory.HAMMER: "молоток",
            ProductCategory.TIRE: "шина"
        }
        
        unit_key = unit_keys.get(category)
        if unit_key and unit_key in unit_validation:
            valid_units = unit_validation[unit_key]
            
            # Check if original unit is valid
            if product.original_unit.lower() in [u.lower() for u in valid_units]:
                return valid_units[0]  # Return standard form
        
        # Default to original unit
        return product.original_unit
    
    async def _generate_output(self, products: List[Product], 
                             original_file: str,
                             output_dir: str) -> Path:
        """Generate output Excel file"""
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        original_name = Path(original_file).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_path / f"{original_name}_normalized_{timestamp}.xlsx"
        
        # Export using parser
        self.parser.export_normalized(products, str(output_file), original_file)
        
        # Also generate summary report
        summary_file = output_path / f"{original_name}_summary_{timestamp}.json"
        summary = self._generate_summary(products)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Generated output files: {output_file}, {summary_file}")
        return output_file
    
    def _generate_summary(self, products: List[Product]) -> Dict[str, Any]:
        """Generate processing summary"""
        summary = {
            "processing_date": datetime.now().isoformat(),
            "total_products": len(products),
            "statistics": {
                "completed": sum(1 for p in products if p.status == ProcessingStatus.COMPLETED),
                "rejected": sum(1 for p in products if p.status == ProcessingStatus.REJECTED),
                "failed": sum(1 for p in products if p.status == ProcessingStatus.FAILED),
                "pending": sum(1 for p in products if p.status == ProcessingStatus.PENDING)
            },
            "category_distribution": {},
            "rejection_reasons": {},
            "processing_errors": []
        }
        
        # Category distribution
        for product in products:
            cat_name = product.category.value
            if cat_name not in summary["category_distribution"]:
                summary["category_distribution"][cat_name] = 0
            summary["category_distribution"][cat_name] += 1
        
        # Rejection reasons
        for product in products:
            if product.status == ProcessingStatus.REJECTED and product.comment:
                reason = product.comment
                if reason not in summary["rejection_reasons"]:
                    summary["rejection_reasons"][reason] = 0
                summary["rejection_reasons"][reason] += 1
        
        # Processing errors
        for product in products:
            if product.status == ProcessingStatus.FAILED:
                summary["processing_errors"].append({
                    "product_code": product.internal_code,
                    "product_name": product.original_name,
                    "error": product.error_message
                })
        
        return summary


class AsyncMTRProcessor(MTRProcessor):
    """Enhanced async version with better concurrency handling"""
    
    async def process_multiple_files(self, file_paths: List[str], 
                                   output_dir: str) -> List[Dict[str, Any]]:
        """Process multiple files concurrently"""
        tasks = [self.process_file(fp, output_dir) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        processed_results = []
        for file_path, result in zip(file_paths, results):
            if isinstance(result, Exception):
                processed_results.append({
                    "file": file_path,
                    "status": "error",
                    "error": str(result)
                })
            else:
                result["file"] = file_path
                processed_results.append(result)
        
        return processed_results
