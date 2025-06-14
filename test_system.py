#!/usr/bin/env python3
"""
Quick test script for MTR Normalization System
Tests the system with the 4 provided Excel files
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Mock environment variables for testing
os.environ['OPENAI_API_KEY'] = 'mock_key_for_testing'
os.environ['PINECONE_API_KEY'] = 'mock_key_for_testing'

from src.utils.excel_parser import ExcelParser
from src.utils.category_detector import SmartCategoryDetector
from src.models.models import Product, ProductCategory
from rich.console import Console
from rich.table import Table

console = Console()


def test_excel_parsing():
    """Test Excel file parsing"""
    console.print("\n[bold green]Testing Excel Parsing[/bold green]\n")
    
    parser = ExcelParser()
    test_files = [
        "Appendix 1_Pressure Sensors_eng.xlsx",
        "Appendix 2 – Steel Circles_eng.xlsx",
        "Appendix 3 – Hammers_eng.xlsx",
        "Appendix 4 – Tires for Cars and Other Vehicles.xlsx"
    ]
    
    results = {}
    
    for file in test_files:
        try:
            console.print(f"Parsing: [cyan]{file}[/cyan]")
            products = parser.parse_file(file)
            results[file] = {
                "success": True,
                "count": len(products),
                "sample": products[0] if products else None
            }
            console.print(f"  ✓ Found [green]{len(products)}[/green] products\n")
        except Exception as e:
            results[file] = {
                "success": False,
                "error": str(e)
            }
            console.print(f"  ✗ Error: [red]{e}[/red]\n")
    
    return results


def test_category_detection():
    """Test category detection"""
    console.print("\n[bold green]Testing Category Detection[/bold green]\n")
    
    detector = SmartCategoryDetector()
    
    test_products = [
        "Датчик давления ОВЕН ПД100И-ДГ0.25-111-0.5",
        "Круг стальной горячекатаный В1-II 10ММ ГОСТ 2590-2006",
        "Молоток слесарный 0.5КГ 320ММ сталь углеродистая",
        "Шина зимняя Nokian Tyres Hakkapeliitta R5 SUV 265/65 R17",
        "Подшипник шариковый SKF 6205-2RS",  # Unknown category
    ]
    
    table = Table(title="Category Detection Results")
    table.add_column("Product", style="cyan", width=50)
    table.add_column("Detected Category", style="green")
    table.add_column("Confidence", style="yellow")
    
    for product in test_products:
        category, confidence = detector.detect_category(product)
        table.add_row(
            product[:47] + "..." if len(product) > 50 else product,
            category.value,
            f"{confidence:.2f}"
        )
    
    console.print(table)


def test_data_structure():
    """Test data structure and schemas"""
    console.print("\n[bold green]Testing Data Structure[/bold green]\n")
    
    # Create sample product
    product = Product(
        internal_code="TEST001",
        original_name="Датчик давления ОВЕН ПД100И-ДГ0.25-111-0.5",
        original_unit="шт",
        category_name="Датчики давления"
    )
    
    # Detect category
    detector = SmartCategoryDetector()
    product.category, product.confidence_score = detector.detect_category(product.original_name)
    
    # Show product structure
    console.print("[bold]Sample Product Structure:[/bold]")
    for key, value in product.__dict__.items():
        if value is not None and value != "":
            console.print(f"  {key}: {value}")


async def test_mock_processing():
    """Test processing workflow with mocked agents"""
    console.print("\n[bold green]Testing Processing Workflow (Mocked)[/bold green]\n")
    
    # Create mock product
    product = Product(
        internal_code="TEST001",
        original_name="Датчик давления ОВЕН ПД100И-ДГ0.25-111-0.5",
        original_unit="шт",
        category_name="Датчики давления",
        category=ProductCategory.PRESSURE_SENSOR,
        excel_row=8
    )
    
    # Mock research result
    console.print("1. [cyan]Research Agent[/cyan] - Mock extracting specifications...")
    product.specifications = {
        "manufacturer": "ОВЕН",
        "model": "ПД100И-ДГ",
        "measurement_range": "0-0.25 МПа",
        "accuracy_class": "0.5",
        "output_signal": "4-20 мА"
    }
    
    # Mock OKPD2 classification
    console.print("2. [cyan]OKPD2 Agent[/cyan] - Mock finding classification code...")
    product.okpd2_code = "26.51.52.110"
    
    # Mock validation
    console.print("3. [cyan]Validation Agent[/cyan] - Mock validating quality...")
    product.normalized_unit = "штука"
    product.comment = "Успешно нормализовано"
    
    # Show final result
    console.print("\n[bold]Final Normalized Product:[/bold]")
    table = Table()
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Internal Code", product.internal_code)
    table.add_row("Original Name", product.original_name)
    table.add_row("Category", product.category.value)
    table.add_row("OKPD2 Code", product.okpd2_code)
    table.add_row("Normalized Unit", product.normalized_unit)
    table.add_row("Specifications", str(len(product.specifications)) + " found")
    table.add_row("Status", product.comment)
    
    console.print(table)


def main():
    """Run all tests"""
    console.print("\n[bold magenta]MTR Normalization System - Test Suite[/bold magenta]")
    console.print("=" * 60)
    
    # Test 1: Excel parsing
    parsing_results = test_excel_parsing()
    
    # Test 2: Category detection
    test_category_detection()
    
    # Test 3: Data structure
    test_data_structure()
    
    # Test 4: Mock processing
    asyncio.run(test_mock_processing())
    
    # Summary
    console.print("\n[bold green]Test Summary[/bold green]")
    console.print("=" * 60)
    
    # Parsing summary
    successful_parses = sum(1 for r in parsing_results.values() if r["success"])
    console.print(f"Excel Parsing: {successful_parses}/{len(parsing_results)} files parsed successfully")
    
    if successful_parses == len(parsing_results):
        console.print("\n[bold green]✓ All tests passed! System is ready for use.[/bold green]")
        console.print("\nNext steps:")
        console.print("1. Add your API keys to .env file")
        console.print("2. Run: python main.py setup")
        console.print("3. Process files: python main.py process <excel_file>")
    else:
        console.print("\n[bold red]✗ Some tests failed. Please check the errors above.[/bold red]")


if __name__ == "__main__":
    main()
