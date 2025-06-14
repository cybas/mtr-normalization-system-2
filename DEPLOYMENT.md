# MTR Normalization System - Deployment Guide

## 🚀 Quick Deployment Steps

### 1. System Requirements

- Python 3.8+
- 8GB+ RAM (16GB recommended for large files)
- 10GB+ free disk space
- Internet connection for API calls

### 2. Installation

```bash
# Clone repository
git clone <your-repo-url>
cd mtr-normalization-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. API Keys Setup

Get your API keys:

1. **OpenAI API Key**
   - Go to https://platform.openai.com/api-keys
   - Create new secret key
   - Add to `.env`: `OPENAI_API_KEY=sk-...`

2. **Pinecone API Key** (Optional but recommended)
   - Sign up at https://www.pinecone.io/
   - Create new project
   - Get API key from console
   - Add to `.env`: `PINECONE_API_KEY=...`

### 4. First Run

```bash
# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Run setup
python main.py setup

# Test the system
python test_system.py

# Process your first file
python main.py process "Appendix 1_Pressure Sensors_eng.xlsx"
```

### 5. Production Configuration

For production use, optimize these settings in `.env`:

```bash
# Increase for better performance
BATCH_SIZE=50
MAX_WORKERS=8
MAX_RETRIES=5

# Use GPT-4 Turbo for best results
OPENAI_MODEL=gpt-4-turbo-preview

# Enable caching
CACHE_EMBEDDINGS=True
```

### 6. Processing Your Files

Place your Excel files in `data/input/` then:

```bash
# Single file
python main.py process data/input/your_file.xlsx

# Batch processing
python main.py batch data/input/

# With custom output
python main.py process input.xlsx -o /path/to/output
```

### 7. Monitoring Progress

The system provides:
- Real-time progress indicators
- Detailed logs in `logs/`
- Summary reports in output directory
- Processing statistics

### 8. Handling Large Files (40,000+ rows)

For massive files:

```bash
# Set environment for large processing
export BATCH_SIZE=100
export MAX_WORKERS=10

# Use screen/tmux for long runs
screen -S mtr_processing
python main.py process massive_file.xlsx

# Detach with Ctrl+A, D
# Reattach with: screen -r mtr_processing
```

### 9. Cost Management

Monitor your API usage:
- Check OpenAI dashboard regularly
- Set usage limits in OpenAI account
- Use caching to reduce duplicate calls
- Process in batches during off-peak

### 10. Troubleshooting

Common issues:

**"API Key not found"**
- Check `.env` file exists
- Verify key format (no quotes needed)

**"Rate limit exceeded"**
- Reduce MAX_WORKERS
- Add delays between batches

**"Out of memory"**
- Reduce BATCH_SIZE
- Process smaller file chunks

**"Connection timeout"**
- Check internet connection
- Increase timeout values

## 📞 Support

- Check logs: `tail -f logs/mtr_normalization.log`
- Run diagnostics: `python main.py info`
- Test specific category: `python main.py test sensor`

## 🎉 You're Ready!

Start processing your MTR data:

```bash
python main.py process your_excel_file.xlsx
```

The system will:
1. ✅ Auto-detect product categories
2. ✅ Research specifications
3. ✅ Find OKPD2 codes
4. ✅ Validate quality
5. ✅ Generate normalized Excel output

Happy normalizing! 🚀
