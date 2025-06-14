"""
Core Data Models for MTR Normalization System
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class ProductCategory(Enum):
    """Product category enumeration"""
    PRESSURE_SENSOR = "PRESSURE_SENSOR"
    STEEL_CIRCLE = "STEEL_CIRCLE"
    HAMMER = "HAMMER"
    TIRE = "TIRE"
    UNKNOWN = "UNKNOWN"


class ProcessingStatus(Enum):
    """Processing status enumeration"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


@dataclass
class Product:
    """Base product model"""
    # Original data
    internal_code: str
    original_name: str
    original_unit: str
    category_name: str
    
    # Detected/processed data
    category: ProductCategory = ProductCategory.UNKNOWN
    
    # Normalized data (to be filled)
    normalized_unit: Optional[str] = None
    okpd2_code: Optional[str] = None
    comment: Optional[str] = None
    specifications: Dict[str, Any] = field(default_factory=dict)
    
    # Processing metadata
    status: ProcessingStatus = ProcessingStatus.PENDING
    processing_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    confidence_score: float = 0.0
    
    # Row reference
    excel_row: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "internal_code": self.internal_code,
            "original_name": self.original_name,
            "original_unit": self.original_unit,
            "category_name": self.category_name,
            "category": self.category.value,
            "normalized_unit": self.normalized_unit,
            "okpd2_code": self.okpd2_code,
            "comment": self.comment,
            "specifications": self.specifications,
            "status": self.status.value,
            "processing_timestamp": self.processing_timestamp.isoformat() if self.processing_timestamp else None,
            "error_message": self.error_message,
            "confidence_score": self.confidence_score,
            "excel_row": self.excel_row
        }


@dataclass
class ResearchResult:
    """Result from product research"""
    product_name: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    specifications: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class OKPD2Result:
    """Result from OKPD2 classification"""
    code: str
    name: str
    level: int
    parent_code: Optional[str] = None
    confidence: float = 0.0
    alternative_codes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result from quality validation"""
    is_valid: bool
    issues: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ProcessingBatch:
    """Batch of products for processing"""
    batch_id: str
    products: List[Product]
    category: ProductCategory
    total_count: int
    processed_count: int = 0
    failed_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.processed_count == 0:
            return 0.0
        return (self.processed_count - self.failed_count) / self.processed_count


@dataclass
class EmbeddingData:
    """Embedding data for vector storage"""
    product_id: str
    text: str
    embedding: List[float]
    category: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CachedProduct:
    """Cached product information"""
    original_name: str
    normalized_data: Dict[str, Any]
    embedding: Optional[List[float]] = None
    last_used: datetime = field(default_factory=datetime.now)
    use_count: int = 1
