# MTR Normalization System 🚀

An intelligent automation system for normalizing Russian industrial procurement data (Material and Technical Resources) using AI-powered processing.

## 🎯 Overview

This system automates the manual process of normalizing product data in Excel files by:
- **Auto-detecting** product categories from mixed data
- **Researching** technical specifications using web search
- **Finding** OKPD2 classification codes from classifikators.ru
- **Validating** data quality according to Russian compliance rules
- **Scaling** from 4 neat files to 40,000+ mixed rows

## 🏗️ Architecture

```
Excel Input → Category Detection → 3-AI Research Chain → Normalized Output
                                   ↓
                            🤖 Research Agent
                            🤖 OKPD2 Classifier  
                            🤖 Quality Validator
```

## 📋 Features

- **Smart Category Detection**: Automatically identifies product types using pattern matching and AI
- **Parallel Processing**: Handles multiple products concurrently for speed
- **Intelligent Caching**: Learns from processed products to speed up similar items
- **Compliance Rules**: Built-in Russian MTR compliance validation
- **Flexible Output**: Preserves original Excel structure while adding normalized data
- **Detailed Reporting**: Generates processing statistics and rejection reasons

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository_url>
cd mtr-normalization-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys:
# - OPENAI_API_KEY
# - PINECONE_API_KEY (optional)
```

### 3. Setup

```bash
# Run setup wizard
python main.py setup

# Test the system
python test_system.py
```

### 4. Process Files

```bash
# Process single file
python main.py process "Appendix 1_Pressure Sensors_eng.xlsx"

# Process with custom output directory
python main.py process "input.xlsx" -o "./results"

# Batch process multiple files
python main.py batch "./data/input" -p "*.xlsx"

# Dry run (parse only, no processing)
python main.py process "input.xlsx" --dry-run
```

## 📊 Supported Product Categories

| Category | Examples | OKPD2 Prefix |
|----------|----------|--------------|
| **Pressure Sensors** | Датчики давления, преобразователи | 26.51.52 |
| **Steel Circles** | Круг стальной, прокат | 24.10.75 |
| **Hammers** | Молотки слесарные | 25.73.30 |
| **Tires** | Шины автомобильные | 22.11.11 |
| **Unknown** | Auto-detected and learned | Dynamic |

## 🔧 Advanced Usage

### Using Different LLM Providers

```python
# In .env file:
# For Claude/Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key

# For local models
LLM_PROVIDER=local
LOCAL_MODEL_PATH=./models/your_model
```

### Custom Category Configuration

Edit `config/config.py` to add new product categories:

```python
PRODUCT_CATEGORIES["YOUR_CATEGORY"] = {
    "keywords": ["keyword1", "keyword2"],
    "unit": "штука",
    "okpd2_prefix": "XX.XX.XX",
    "schema": ["field1", "field2", ...]
}
```

### Processing Large Files (40,000+ rows)

```bash
# Increase batch size and workers for large files
export BATCH_SIZE=50
export MAX_WORKERS=8

python main.py process "large_file.xlsx"
```

## 📈 Performance

| Metric | Value |
|--------|-------|
| Products/minute | ~100-150 |
| API calls/product | 3-5 |
| Cache hit rate | ~30-40% |
| Success rate | ~85-95% |

## 💰 Cost Estimation

| Products | Estimated Cost |
|----------|----------------|
| 1,000 | ~$15-20 |
| 10,000 | ~$150-200 |
| 40,000 | ~$600-800 |

*Costs vary based on product complexity and cache hits*

## 🛠️ Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_category_detector.py
```

### Adding New Features

1. Create feature branch
2. Add tests in `tests/`
3. Implement in `src/`
4. Update documentation
5. Submit PR

## 📝 Compliance Rules

The system enforces Russian MTR compliance:

- ✅ OKPD2 codes at maximum classification level
- ✅ Complete parametric descriptions
- ✅ Validated units of measurement
- ✅ Russian rejection comments for non-compliant items

### Rejection Examples

- "Не подлежит нормализации: артикул не соответствует цвету"
- "Не подлежит нормализации: невозможно определить производителя"
- "Не подлежит нормализации: неполные технические характеристики"

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For issues or questions:
- Check the [test_system.py](test_system.py) for examples
- Review logs in `./logs/`
- Open an issue with error details

## 🎉 Acknowledgments

Built with:
- OpenAI GPT-4 for intelligent processing
- Pinecone for vector similarity search
- Rich for beautiful terminal output
- And lots of ☕ coffee!

---

**Ready to normalize 40,000 products? Let's go! 🚀**
