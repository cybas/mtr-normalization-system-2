"""
MTR Normalization System - Main Entry Point
"""
import asyncio
import click
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.processors.mtr_processor import AsyncMTRProcessor
from src.utils.excel_parser import ExcelParser
from config.config import get_config

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """MTR Normalization System - Automate Russian procurement data normalization"""
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output-dir', '-o', default='./data/output', help='Output directory')
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file path')
@click.option('--dry-run', is_flag=True, help='Parse file without processing')
def process(input_file, output_dir, config, dry_run):
    """Process a single Excel file"""
    console.print(f"\n[bold green]MTR Normalization System[/bold green]")
    console.print(f"Processing: {input_file}\n")
    
    if dry_run:
        # Just parse and analyze
        parser = ExcelParser()
        try:
            products = parser.parse_file(input_file)
            
            # Show analysis
            table = Table(title="File Analysis")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Products", str(len(products)))
            
            # Category distribution
            categories = {}
            for p in products:
                cat = p.category.value
                categories[cat] = categories.get(cat, 0) + 1
            
            for cat, count in categories.items():
                table.add_row(f"Category: {cat}", str(count))
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error parsing file: {e}[/red]")
            return
    
    else:
        # Full processing
        asyncio.run(_process_file(input_file, output_dir))


async def _process_file(input_file: str, output_dir: str):
    """Async file processing with progress tracking"""
    processor = AsyncMTRProcessor()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Add processing task
        task = progress.add_task("Processing products...", total=None)
        
        try:
            # Process file
            result = await processor.process_file(input_file, output_dir)
            
            if result["status"] == "success":
                # Show results
                stats = result["statistics"]
                
                table = Table(title="Processing Results")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")
                
                table.add_row("Total Processed", str(stats["total_processed"]))
                table.add_row("Successful", str(stats["successful"]))
                table.add_row("Rejected", str(stats["rejected"]))
                table.add_row("Failed", str(stats["failed"]))
                table.add_row("Processing Time", f"{stats['processing_time']:.2f}s")
                table.add_row("Output File", result["output_file"])
                
                console.print("\n")
                console.print(table)
                console.print("\n[bold green]✓ Processing completed successfully![/bold green]")
                
            else:
                console.print(f"\n[red]✗ Processing failed: {result['error']}[/red]")
                
        except Exception as e:
            console.print(f"\n[red]✗ Unexpected error: {e}[/red]")
            logger.exception("Processing failed")


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--output-dir', '-o', default='./data/output', help='Output directory')
@click.option('--pattern', '-p', default='*.xlsx', help='File pattern to match')
def batch(input_dir, output_dir, pattern):
    """Process multiple Excel files in a directory"""
    console.print(f"\n[bold green]MTR Batch Processing[/bold green]")
    console.print(f"Input directory: {input_dir}")
    console.print(f"Pattern: {pattern}\n")
    
    # Find files
    input_path = Path(input_dir)
    files = list(input_path.glob(pattern))
    
    if not files:
        console.print(f"[yellow]No files found matching pattern: {pattern}[/yellow]")
        return
    
    console.print(f"Found {len(files)} files to process\n")
    
    # Process files
    asyncio.run(_process_batch(files, output_dir))


async def _process_batch(files: list, output_dir: str):
    """Process multiple files"""
    processor = AsyncMTRProcessor()
    
    results = await processor.process_multiple_files(
        [str(f) for f in files], 
        output_dir
    )
    
    # Show summary
    table = Table(title="Batch Processing Summary")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Products", style="yellow")
    table.add_column("Time (s)", style="magenta")
    
    total_success = 0
    total_products = 0
    
    for result in results:
        file_name = Path(result["file"]).name
        status = "✓" if result["status"] == "success" else "✗"
        
        if result["status"] == "success":
            stats = result["statistics"]
            products = str(stats["total_processed"])
            time = f"{stats['processing_time']:.1f}"
            total_success += 1
            total_products += stats["total_processed"]
        else:
            products = "-"
            time = "-"
        
        table.add_row(file_name, status, products, time)
    
    console.print(table)
    console.print(f"\n[bold]Summary:[/bold] {total_success}/{len(files)} files processed successfully")
    console.print(f"Total products normalized: {total_products}")


@cli.command()
@click.argument('category', type=click.Choice(['sensor', 'steel', 'hammer', 'tire', 'all']))
def test(category):
    """Test processing with sample data"""
    console.print(f"\n[bold green]Testing {category} processing...[/bold green]\n")
    
    # Create test data
    test_products = {
        'sensor': [
            "Датчик давления ОВЕН ПД100И-ДГ0.25-111-0.5",
            "Датчик дав. Endress+Hauser Cerabar S PMP75 AAA1PB8",
            "Преобразователь давления Danfoss MBS 3000 060G1109"
        ],
        'steel': [
            "Круг стальной горячекатаный В1-II 10ММ ГОСТ 2590-2006 СТ3СП",
            "Круг сталь 20 диаметр 50мм ГОСТ 1050-2013",
            "Круг стальной 40Х диам 100мм длина 6м"
        ],
        'hammer': [
            "Молоток слесарный 0.5КГ 320ММ сталь углеродистая",
            "Молоток электромонтажника Stanley STHT0-51906 300г",
            "Молоток-гвоздодер Gross 10605 450г фиберглас"
        ],
        'tire': [
            "Шина зимняя Nokian Tyres Hakkapeliitta R5 SUV 265/65 R17",
            "Шина всесезонная BFGoodrich All Terrain T/A KO2 265/70 R16",
            "Шина летняя Michelin Pilot Sport 4 225/45 R17 94Y"
        ]
    }
    
    # Run test processing
    if category == 'all':
        test_items = []
        for items in test_products.values():
            test_items.extend(items)
    else:
        test_items = test_products.get(category, [])
    
    asyncio.run(_test_processing(test_items))


async def _test_processing(test_items: list):
    """Test processing on sample items"""
    from src.utils.category_detector import SmartCategoryDetector
    from src.models.models import Product
    
    detector = SmartCategoryDetector()
    
    table = Table(title="Category Detection Test")
    table.add_column("Product", style="cyan", width=50)
    table.add_column("Category", style="green")
    table.add_column("Confidence", style="yellow")
    
    for item in test_items:
        # Create test product
        product = Product(
            internal_code=f"TEST_{test_items.index(item)}",
            original_name=item,
            original_unit="шт",
            category_name="Test"
        )
        
        # Detect category
        category, confidence = detector.detect_category(item)
        product.category = category
        product.confidence_score = confidence
        
        table.add_row(
            item[:50] + "..." if len(item) > 50 else item,
            category.value,
            f"{confidence:.2f}"
        )
    
    console.print(table)


@cli.command()
def setup():
    """Setup wizard for first-time configuration"""
    console.print("\n[bold green]MTR Normalization System Setup[/bold green]\n")
    
    # Check for .env file
    if not Path(".env").exists():
        console.print("[yellow]No .env file found. Creating from template...[/yellow]")
        
        # Copy .env.example to .env
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            console.print("[green]✓ Created .env file[/green]")
        else:
            console.print("[red]✗ .env.example not found![/red]")
            return
    
    # Check API keys
    console.print("\n[bold]Checking API keys...[/bold]")
    
    required_keys = ["OPENAI_API_KEY", "PINECONE_API_KEY"]
    missing_keys = []
    
    for key in required_keys:
        if not os.getenv(key) or os.getenv(key) == f"your_{key.lower()}_here":
            missing_keys.append(key)
            console.print(f"[red]✗ {key} not configured[/red]")
        else:
            console.print(f"[green]✓ {key} configured[/green]")
    
    if missing_keys:
        console.print(f"\n[yellow]Please edit .env file and add the missing API keys:[/yellow]")
        for key in missing_keys:
            console.print(f"  - {key}")
    else:
        console.print("\n[green]✓ All API keys configured![/green]")
    
    # Create directories
    console.print("\n[bold]Creating directories...[/bold]")
    
    dirs = ["data/input", "data/output", "data/processed", "logs"]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓ {dir_path}[/green]")
    
    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("You can now run: mtr process <excel_file>")


@cli.command()
def info():
    """Show system information and configuration"""
    config = get_config()
    
    console.print("\n[bold green]MTR Normalization System[/bold green]")
    console.print("Version: 1.0.0\n")
    
    # Configuration info
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("LLM Model", config["api"]["openai"]["model"])
    table.add_row("Embedding Model", config["api"]["openai"]["embedding_model"])
    table.add_row("Batch Size", str(config["processing"]["batch_size"]))
    table.add_row("Max Workers", str(config["processing"]["parallel_workers"]))
    table.add_row("Vector DB", "Pinecone" if config["api"]["pinecone"]["api_key"] else "Not configured")
    
    console.print(table)
    
    # Categories info
    console.print("\n[bold]Supported Categories:[/bold]")
    for category, info in config["categories"].items():
        console.print(f"  • {category}: {', '.join(info['keywords'][:3])}...")


if __name__ == "__main__":
    cli()
