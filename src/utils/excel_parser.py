"""
Excel Parser for MTR Files
Handles both categorized and mixed product Excel files
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from src.models.models import Product, ProductCategory
from src.utils.category_detector import SmartCategoryDetector
from config.config import PRODUCT_CATEGORIES

logger = logging.getLogger(__name__)


class ExcelParser:
    """
    Robust Excel parser that handles:
    - Multiple sheet formats
    - Russian/English headers
    - Mixed product categories
    - Various data layouts
    """
    
    def __init__(self):
        self.category_detector = SmartCategoryDetector()
        self.header_mappings = self._initialize_header_mappings()
        
    def _initialize_header_mappings(self) -> Dict[str, str]:
        """Initialize header name mappings (Russian -> English)"""
        return {
            # Core columns
            "Наименование категории": "category_name",
            "Внутренний код организации": "internal_code",
            "Наименование исходное": "original_name",
            "Единица измерения исходная": "original_unit",
            "Единица измерения": "normalized_unit",
            "ОКПД2": "okpd2_code",
            "Комментарий": "comment",
            
            # English versions
            "Category name": "category_name",
            "Internal organization code": "internal_code", 
            "Initial name": "original_name",
            "Initial unit of measurement": "original_unit",
            "Unit of measurement": "normalized_unit",
            "OKPD2": "okpd2_code",
            "Comment": "comment"
        }
    
    def parse_file(self, file_path: str) -> List[Product]:
        """
        Parse Excel file and return list of products
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List[Product]: Parsed products
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Parsing file: {file_path}")
        
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            
            # Find main data sheet
            main_sheet = self._find_main_sheet(excel_file)
            if main_sheet is None:
                raise ValueError("Could not find main data sheet")
            
            # Parse the main sheet
            products = self._parse_sheet(excel_file, main_sheet)
            
            logger.info(f"Parsed {len(products)} products from {file_path}")
            return products
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}")
            raise
    
    def _find_main_sheet(self, excel_file: pd.ExcelFile) -> Optional[str]:
        """Find the main data sheet"""
        sheet_names = excel_file.sheet_names
        
        # Common patterns for main sheets
        main_patterns = [
            "отчет", "недостающие", "данные", "data", "main", "products"
        ]
        
        for sheet in sheet_names:
            sheet_lower = sheet.lower()
            if any(pattern in sheet_lower for pattern in main_patterns):
                return sheet
        
        # Default to first sheet
        return sheet_names[0] if sheet_names else None
    
    def _parse_sheet(self, excel_file: pd.ExcelFile, sheet_name: str) -> List[Product]:
        """Parse a specific sheet"""
        df = excel_file.parse(sheet_name)
        
        # Find header row
        header_row = self._find_header_row(df)
        if header_row is None:
            raise ValueError("Could not find header row")
        
        # Re-read with proper header
        df = excel_file.parse(sheet_name, header=header_row)
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Map columns
        column_mapping = self._map_columns(df.columns)
        
        # Extract products
        products = []
        for idx, row in df.iterrows():
            product = self._extract_product(row, column_mapping, idx + header_row + 2)
            if product:
                products.append(product)
        
        return products
    
    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """Find the row containing headers"""
        # Look for rows with multiple non-null values
        for i in range(min(20, len(df))):
            row = df.iloc[i]
            non_null_count = row.notna().sum()
            
            # Check if this row contains known headers
            row_values = [str(val).strip() for val in row if pd.notna(val)]
            header_matches = sum(1 for val in row_values 
                               if val in self.header_mappings)
            
            if header_matches >= 3 or non_null_count >= 5:
                return i
        
        return None
    
    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """Map DataFrame columns to standard names"""
        mapping = {}
        
        for col in columns:
            col_clean = col.strip()
            if col_clean in self.header_mappings:
                mapping[col] = self.header_mappings[col_clean]
            else:
                # Keep original column name
                mapping[col] = col_clean.lower().replace(" ", "_")
        
        return mapping
    
    def _extract_product(self, row: pd.Series, 
                        column_mapping: Dict[str, str], 
                        excel_row: int) -> Optional[Product]:
        """Extract product from row"""
        # Check if row has required data
        required_fields = ["original_name", "internal_code", "original_unit"]
        
        # Get mapped values
        mapped_data = {}
        for orig_col, mapped_col in column_mapping.items():
            if pd.notna(row.get(orig_col)):
                mapped_data[mapped_col] = str(row[orig_col]).strip()
        
        # Check required fields
        missing_required = [field for field in required_fields 
                          if field not in mapped_data or not mapped_data[field]]
        
        if missing_required:
            return None
        
        # Create product
        product = Product(
            internal_code=mapped_data.get("internal_code", ""),
            original_name=mapped_data.get("original_name", ""),
            original_unit=mapped_data.get("original_unit", ""),
            category_name=mapped_data.get("category_name", "Unknown"),
            excel_row=excel_row
        )
        
        # Pre-fill if already normalized
        if "normalized_unit" in mapped_data:
            product.normalized_unit = mapped_data["normalized_unit"]
        if "okpd2_code" in mapped_data:
            product.okpd2_code = mapped_data["okpd2_code"]
        if "comment" in mapped_data:
            product.comment = mapped_data["comment"]
        
        # Detect category
        category, confidence = self.category_detector.detect_category(product.original_name)
        product.category = category
        product.confidence_score = confidence
        
        # Extract any specification columns
        spec_columns = [col for col in mapped_data.keys() 
                       if col not in ["internal_code", "original_name", 
                                     "original_unit", "category_name",
                                     "normalized_unit", "okpd2_code", "comment"]]
        
        for spec_col in spec_columns:
            if mapped_data.get(spec_col):
                product.specifications[spec_col] = mapped_data[spec_col]
        
        return product
    
    def parse_mixed_file(self, file_path: str) -> Dict[ProductCategory, List[Product]]:
        """
        Parse mixed product file and group by category
        
        Returns:
            Dict[ProductCategory, List[Product]]: Products grouped by category
        """
        products = self.parse_file(file_path)
        
        # Group by category
        categorized = {}
        for product in products:
            if product.category not in categorized:
                categorized[product.category] = []
            categorized[product.category].append(product)
        
        # Log distribution
        logger.info("Product distribution:")
        for category, prods in categorized.items():
            logger.info(f"  {category.value}: {len(prods)} products")
        
        return categorized
    
    def export_normalized(self, products: List[Product], 
                         output_path: str,
                         original_file_path: str):
        """
        Export normalized products back to Excel format
        Preserves original structure and adds normalized data
        """
        # Read original file structure
        original_df = pd.read_excel(original_file_path, sheet_name=0)
        
        # Create product lookup by row
        product_by_row = {p.excel_row: p for p in products}
        
        # Update DataFrame with normalized data
        for excel_row, product in product_by_row.items():
            if excel_row <= len(original_df):
                row_idx = excel_row - 1
                
                # Update normalized columns
                if "Единица измерения" in original_df.columns:
                    original_df.loc[row_idx, "Единица измерения"] = product.normalized_unit
                if "ОКПД2" in original_df.columns:
                    original_df.loc[row_idx, "ОКПД2"] = product.okpd2_code
                if "Комментарий" in original_df.columns:
                    original_df.loc[row_idx, "Комментарий"] = product.comment
                
                # Add specifications to appropriate columns
                for spec_name, spec_value in product.specifications.items():
                    # Find matching column
                    for col in original_df.columns:
                        if spec_name.lower() in col.lower():
                            original_df.loc[row_idx, col] = spec_value
                            break
        
        # Save to new file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            original_df.to_excel(writer, index=False, sheet_name="Normalized Data")
            
            # Add metadata sheet
            metadata = pd.DataFrame({
                "Параметр": ["Дата обработки", "Количество продуктов", 
                            "Успешно нормализовано", "Отклонено"],
                "Значение": [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    len(products),
                    sum(1 for p in products if p.status.value == "COMPLETED"),
                    sum(1 for p in products if p.status.value == "REJECTED")
                ]
            })
            metadata.to_excel(writer, index=False, sheet_name="Metadata")
        
        logger.info(f"Exported normalized data to {output_path}")
