"""
Quality Validation Agent
Validates data quality and compliance with Russian MTR standards
"""
import json
from typing import Dict, Any, List, Optional
import logging

from src.agents.base_agent import BaseAgent
from src.models.models import Product, ValidationResult, ProductCategory, ProcessingStatus
from config.config import COMPLIANCE_RULES, PRODUCT_CATEGORIES

logger = logging.getLogger(__name__)


class QualityValidationAgent(BaseAgent):
    """
    AI Agent 3: Quality Validator
    - Double-checks all research and OKPD2 codes
    - Ensures complete parametric description
    - Identifies quality issues
    - Applies rejection rules
    """
    
    def __init__(self):
        super().__init__("QualityValidationAgent")
        self.compliance_rules = COMPLIANCE_RULES
        self.validation_criteria = self._load_validation_criteria()
        
    def _load_validation_criteria(self) -> Dict[ProductCategory, Dict[str, Any]]:
        """Load category-specific validation criteria"""
        return {
            ProductCategory.PRESSURE_SENSOR: {
                "required_specs": [
                    "measurement_range", "accuracy_class", "output_signal"
                ],
                "optional_specs": [
                    "protection_degree", "temperature_range", "material"
                ],
                "unit_options": ["штука", "шт", "шт."],
                "min_specs_count": 5
            },
            ProductCategory.STEEL_CIRCLE: {
                "required_specs": [
                    "diameter_mm", "steel_grade", "standard"
                ],
                "optional_specs": [
                    "length", "hardness", "surface_quality"
                ],
                "unit_options": ["тонна", "т", "тн"],
                "min_specs_count": 4
            },
            ProductCategory.HAMMER: {
                "required_specs": [
                    "striker_weight_kg", "length_mm", "type"
                ],
                "optional_specs": [
                    "handle_material", "standard", "brand"
                ],
                "unit_options": ["штука", "шт", "шт."],
                "min_specs_count": 4
            },
            ProductCategory.TIRE: {
                "required_specs": [
                    "width", "profile", "diameter", "season"
                ],
                "optional_specs": [
                    "speed_index", "load_index", "brand", "model"
                ],
                "unit_options": ["штука", "шт", "шт."],
                "min_specs_count": 5
            }
        }
    
    async def process(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate product normalization"""
        product = context["product"]
        research_result = context.get("research_result")
        okpd2_result = context.get("okpd2_result")
        category = context.get("category", ProductCategory.UNKNOWN)
        
        logger.info(f"Validating: {product.original_name}")
        
        # Initialize validation result
        issues = []
        suggestions = []
        
        # Step 1: Validate category detection
        if category == ProductCategory.UNKNOWN:
            issues.append("Не удалось определить категорию продукта")
        
        # Step 2: Validate OKPD2 code
        okpd2_issues = self._validate_okpd2(okpd2_result, category)
        issues.extend(okpd2_issues)
        
        # Step 3: Validate specifications completeness
        spec_issues = self._validate_specifications(
            research_result, category, product
        )
        issues.extend(spec_issues)
        
        # Step 4: Validate unit of measurement
        unit_issue = self._validate_unit(product, category)
        if unit_issue:
            issues.append(unit_issue)
        
        # Step 5: Check for variability issues
        variability_issues = await self._check_variability(
            product, research_result
        )
        issues.extend(variability_issues)
        
        # Step 6: Apply business rules
        rule_violations = self._apply_business_rules(
            product, research_result, okpd2_result
        )
        issues.extend(rule_violations)
        
        # Determine if product should be rejected
        rejection_reason = None
        is_valid = len(issues) == 0
        
        if not is_valid:
            # Determine most critical issue for rejection
            rejection_reason = self._determine_rejection_reason(issues, product)
        
        # Generate suggestions for improvement
        if not is_valid:
            suggestions = await self._generate_suggestions(
                product, issues, research_result
            )
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            rejection_reason=rejection_reason,
            suggestions=suggestions
        )
    
    def _validate_okpd2(self, okpd2_result: Optional[Dict], 
                       category: ProductCategory) -> List[str]:
        """Validate OKPD2 classification"""
        issues = []
        
        if not okpd2_result:
            issues.append("Отсутствует код ОКПД2")
            return issues
        
        # Check code format
        code = okpd2_result.get("code", "")
        if not self._is_valid_okpd2_format(code):
            issues.append(f"Неверный формат кода ОКПД2: {code}")
        
        # Check code level
        level = okpd2_result.get("level", 0)
        if level < 3:
            issues.append(f"Недостаточный уровень детализации ОКПД2 (уровень {level})")
        
        # Check confidence
        confidence = okpd2_result.get("confidence", 0)
        if confidence < 0.5:
            issues.append(f"Низкая уверенность в коде ОКПД2 ({confidence:.2f})")
        
        # Check category alignment
        if category in PRODUCT_CATEGORIES:
            expected_prefix = PRODUCT_CATEGORIES[category.value].get("okpd2_prefix", "")
            if not code.startswith(expected_prefix):
                issues.append(
                    f"Код ОКПД2 {code} не соответствует категории {category.value}"
                )
        
        return issues
    
    def _is_valid_okpd2_format(self, code: str) -> bool:
        """Check if OKPD2 code has valid format"""
        # Format: XX.XX.XX or XX.XX.XX.XXX
        import re
        pattern = r'^\d{2}\.\d{2}\.\d{2}(\.\d{3})?$'
        return bool(re.match(pattern, code))
    
    def _validate_specifications(self, research_result: Optional[Dict],
                               category: ProductCategory,
                               product: Product) -> List[str]:
        """Validate specification completeness"""
        issues = []
        
        if not research_result:
            issues.append("Отсутствуют технические характеристики")
            return issues
        
        specs = research_result.get("specifications", {})
        
        # Get validation criteria for category
        if category not in self.validation_criteria:
            issues.append("Нет критериев валидации для данной категории")
            return issues
        
        criteria = self.validation_criteria[category]
        
        # Check required specifications
        required_specs = criteria.get("required_specs", [])
        missing_required = []
        
        for req_spec in required_specs:
            if req_spec not in specs or not specs[req_spec]:
                missing_required.append(req_spec)
        
        if missing_required:
            issues.append(
                f"Отсутствуют обязательные характеристики: {', '.join(missing_required)}"
            )
        
        # Check minimum specification count
        min_count = criteria.get("min_specs_count", 3)
        actual_count = len([v for v in specs.values() if v])
        
        if actual_count < min_count:
            issues.append(
                f"Недостаточно характеристик ({actual_count} из минимум {min_count})"
            )
        
        # Check for placeholder values
        placeholder_patterns = ["н/д", "n/a", "неизвестно", "unknown", "-", ""]
        placeholders_found = []
        
        for spec_name, spec_value in specs.items():
            if str(spec_value).lower() in placeholder_patterns:
                placeholders_found.append(spec_name)
        
        if placeholders_found:
            issues.append(
                f"Найдены незаполненные характеристики: {', '.join(placeholders_found)}"
            )
        
        return issues
    
    def _validate_unit(self, product: Product, 
                      category: ProductCategory) -> Optional[str]:
        """Validate unit of measurement"""
        if category not in self.validation_criteria:
            return None
        
        criteria = self.validation_criteria[category]
        valid_units = criteria.get("unit_options", [])
        
        # Check if original unit is valid
        if product.original_unit.lower() not in [u.lower() for u in valid_units]:
            return (
                f"Единица измерения '{product.original_unit}' "
                f"не соответствует категории {category.value}. "
                f"Ожидается: {', '.join(valid_units)}"
            )
        
        return None
    
    async def _check_variability(self, product: Product,
                                research_result: Optional[Dict]) -> List[str]:
        """Check for product variability issues"""
        issues = []
        
        # Check for color variations in article
        color_patterns = [
            r'артикул.*цвет', r'article.*color', 
            r'код.*цвет', r'различ.*цвет'
        ]
        
        import re
        for pattern in color_patterns:
            if re.search(pattern, product.original_name, re.IGNORECASE):
                issues.append("Обнаружена вариативность по цвету")
                break
        
        # Check for size variations
        if research_result:
            specs = research_result.get("specifications", {})
            
            # Look for multiple sizes/dimensions
            size_fields = ["diameter", "width", "length", "size"]
            for field in size_fields:
                value = specs.get(field, "")
                if isinstance(value, str) and any(sep in value for sep in ["-", "до", "от"]):
                    issues.append(f"Обнаружена вариативность по параметру: {field}")
        
        return issues
    
    def _apply_business_rules(self, product: Product,
                             research_result: Optional[Dict],
                             okpd2_result: Optional[Dict]) -> List[str]:
        """Apply specific business validation rules"""
        violations = []
        
        # Rule 1: Manufacturer must be identifiable
        if research_result:
            manufacturer = research_result.get("manufacturer")
            if not manufacturer or manufacturer.lower() in ["unknown", "неизвестно"]:
                violations.append("Невозможно определить производителя")
        
        # Rule 2: Model/Article should be specific
        if research_result:
            model = research_result.get("model")
            if model and len(model) < 3:
                violations.append("Модель/артикул слишком короткий")
        
        # Rule 3: Check for generic descriptions
        generic_terms = ["прочие", "другие", "разные", "various", "other", "misc"]
        name_lower = product.original_name.lower()
        if any(term in name_lower for term in generic_terms):
            violations.append("Слишком общее описание продукта")
        
        return violations
    
    def _determine_rejection_reason(self, issues: List[str], 
                                   product: Product) -> str:
        """Determine the primary rejection reason"""
        # Priority order for rejection reasons
        if any("ОКПД2" in issue for issue in issues):
            return "Не подлежит нормализации: отсутствует код ОКПД2"
        
        if any("производител" in issue.lower() for issue in issues):
            return "Не подлежит нормализации: невозможно определить производителя"
        
        if any("вариативность" in issue for issue in issues):
            # Determine type of variability
            if "цвет" in " ".join(issues):
                return "Не подлежит нормализации: артикул не соответствует цвету"
            elif "диаметр" in " ".join(issues) or "размер" in " ".join(issues):
                return "Не подлежит нормализации: вариативность по размеру"
            else:
                return "Не подлежит нормализации: вариативность характеристик"
        
        if any("характеристик" in issue for issue in issues):
            return "Не подлежит нормализации: неполные технические характеристики"
        
        # Default rejection
        return f"Не подлежит нормализации: {issues[0]}"
    
    async def _generate_suggestions(self, product: Product,
                                   issues: List[str],
                                   research_result: Optional[Dict]) -> List[str]:
        """Generate suggestions for fixing issues"""
        prompt = f"""
        Product: {product.original_name}
        Issues found: {json.dumps(issues, ensure_ascii=False)}
        
        Generate 2-3 specific suggestions in Russian for fixing these normalization issues.
        Focus on actionable steps to obtain missing information.
        """
        
        messages = [
            {"role": "system", "content": "You are a data quality expert."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._call_llm(messages, temperature=0.3)
            suggestions = [s.strip() for s in response.split("\n") if s.strip()]
            return suggestions[:3]
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {str(e)}")
            return ["Уточнить информацию у поставщика", "Проверить каталог производителя"]
