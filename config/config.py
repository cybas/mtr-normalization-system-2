"""
MTR Normalization System Configuration
"""
import os
from pathlib import Path
from typing import Dict, Any

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = BASE_DIR / "logs"

# API Configuration
API_CONFIG = {
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "gpt-4o",
        "embedding_model": "text-embedding-3-large",
        "temperature": 0.1,
        "max_tokens": 4000
    },
    "pinecone": {
        "api_key": os.getenv("PINECONE_API_KEY"),
        "environment": os.getenv("PINECONE_ENV", "us-east-1"),
        "index_name": "mtr-products",
        "dimension": 3072  # text-embedding-3-large dimension
    }
}

# Product Categories Configuration
PRODUCT_CATEGORIES = {
    "PRESSURE_SENSOR": {
        "keywords": ["датчик", "давлен", "sensor", "pressure", "преобразователь"],
        "unit": "штука",
        "okpd2_prefix": "26.51.52",
        "schema": [
            "product", "type", "measured_quantity", "trademark_producer",
            "model_article", "identification", "measurement_range",
            "ambient_temperature", "accuracy_class", "output_signal",
            "climate_category", "explosion_protection", "electrical_connector",
            "additional_characteristics", "sensor_mount", "protection_degree",
            "material", "size_mm", "standard", "weight_kg"
        ]
    },
    "STEEL_CIRCLE": {
        "keywords": ["круг", "сталь", "steel", "circle", "прокат"],
        "unit": "тонна",
        "okpd2_prefix": "24.10.75",
        "schema": [
            "product", "hardness", "rolling_accuracy", "curvature_class",
            "diameter_mm", "length", "length_dimension", "standard_assortment",
            "surface_quality", "steel_grade", "standard_material", "weight_ton"
        ]
    },
    "HAMMER": {
        "keywords": ["молот", "hammer"],
        "unit": "штука",
        "okpd2_prefix": "25.73.30",
        "schema": [
            "product", "type", "striker_type", "trademark", "model_designation",
            "article", "striker_weight_kg", "length_mm", "handle_material",
            "handle_type", "standard", "additional_characteristics", "weight_kg"
        ]
    },
    "TIRE": {
        "keywords": ["шина", "tire", "резина", "покрышка"],
        "unit": "штука", 
        "okpd2_prefix": "22.11.11",
        "schema": [
            "product", "season", "spikes_on_tires", "trademark_manufacturer",
            "model", "article", "width", "profile", "diameter", "speed_index",
            "load_index", "extra_load", "construction", "weight_kg"
        ]
    }
}

# Processing Configuration
PROCESSING_CONFIG = {
    "batch_size": 10,
    "max_retries": 3,
    "timeout": 30,
    "parallel_workers": 4,
    "cache_embeddings": True
}

# Russian Compliance Rules
COMPLIANCE_RULES = {
    "rejection_reasons": [
        "Не подлежит нормализации: артикул не соответствует цвету",
        "Не подлежит нормализации: вариативность по диаметру и марке стали",
        "Не подлежит нормализации: неполные технические характеристики",
        "Не подлежит нормализации: отсутствует код ОКПД2",
        "Не подлежит нормализации: невозможно определить производителя"
    ],
    "unit_validation": {
        "датчик": ["штука", "шт", "шт."],
        "круг": ["тонна", "т", "тн"],
        "молоток": ["штука", "шт", "шт."],
        "шина": ["штука", "шт", "шт."]
    }
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": LOGS_DIR / "mtr_normalization.log"
}

# Web Search Configuration
WEB_SEARCH_CONFIG = {
    "search_engine": "google",  # or "bing", "duckduckgo"
    "max_results": 5,
    "timeout": 10,
    "user_agent": "Mozilla/5.0 (compatible; MTR-Normalizer/1.0)"
}

# OKPD2 Classifier Configuration
OKPD2_CONFIG = {
    "base_url": "https://classifikators.ru/okpd",
    "max_depth": 5,  # Maximum classification depth
    "cache_codes": True
}

def get_config() -> Dict[str, Any]:
    """Get complete configuration"""
    return {
        "paths": {
            "base": str(BASE_DIR),
            "input": str(INPUT_DIR),
            "output": str(OUTPUT_DIR),
            "processed": str(PROCESSED_DIR),
            "logs": str(LOGS_DIR)
        },
        "api": API_CONFIG,
        "categories": PRODUCT_CATEGORIES,
        "processing": PROCESSING_CONFIG,
        "compliance": COMPLIANCE_RULES,
        "logging": LOGGING_CONFIG,
        "web_search": WEB_SEARCH_CONFIG,
        "okpd2": OKPD2_CONFIG
    }
