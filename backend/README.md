# BiasFree News - Backend API

FastAPI backend for detecting and removing bias from Bengali news articles using OpenAI GPT-4o-nano.

## Features

- **Bias Detection**: Identify politically charged, emotional, or sensational language
- **Content Debiasing**: Replace biased terms with neutral alternatives
- **Headline Generation**: Create factual, unbiased headlines
- **Web Scraping**: Scrape articles from Prothom Alo, Jugantor, and Samakal
- **Rate Limiting**: Cost control with configurable request limits
- **Production Ready**: Environment-based configuration for local and production

## Tech Stack

- **Framework**: FastAPI 0.115.5
- **AI Model**: OpenAI GPT-4o-nano (cost-optimized)
- **Web Scraping**: BeautifulSoup4 + Requests
- **Validation**: Pydantic 2.10
- **Rate Limiting**: SlowAPI

## Setup Instructions

### 1. Create Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and add your OpenAI API key:

```bash
cp .env.example .env
```

Edit `.env` and set:
```
OPENAI_API_KEY=your_actual_api_key_here
```

### 4. Run Development Server

```bash
# Make sure venv is activated
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or run directly:
```bash
python app/main.py
```

### 5. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## API Endpoints

### POST /api/analyze
Analyze article for bias detection.

**Request:**
```json
{
  "content": "Bengali article text...",
  "title": "Original headline"
}
```

**Response:**
```json
{
  "is_biased": true,
  "bias_score": 75.5,
  "biased_terms": [
    {
      "term": "biased word",
      "reason": "explanation",
      "neutral_alternative": "neutral word",
      "severity": "high"
    }
  ],
  "summary": "Analysis summary",
  "confidence": 0.85
}
```

### POST /api/debias
Debias article content.

### POST /api/generate-headline
Generate neutral headlines.

### POST /api/scrape
Scrape articles from newspapers.

**Request:**
```json
{
  "source": "prothom_alo",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

### POST /api/full-process
Complete pipeline (analyze + debias + headline).

## Configuration

All settings in `.env`:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-nano
OPENAI_MAX_TOKENS=2048
OPENAI_TEMPERATURE=0.3

# Application
ENVIRONMENT=development  # or production
DEBUG=True

# CORS
CORS_ORIGINS=["http://localhost:5173"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=5

# Processing Limits
MAX_ARTICLE_LENGTH=3000
MAX_SCRAPE_ARTICLES=10
```

## Cost Optimization

GPT-4o-nano is highly cost-effective. Additional optimizations:

1. **Content Truncation**: Only first 1500 chars analyzed
2. **Surgical Debiasing**: Replace only identified terms
3. **Rate Limiting**: Prevent abuse
4. **Structured JSON**: Minimizes response tokens

## Production Deployment

### Environment Variables

Set these in your production environment:
- `ENVIRONMENT=production`
- `DEBUG=False`
- `OPENAI_API_KEY=your_production_key`
- `CORS_ORIGINS=["https://yourdomain.com"]`

### Run with Uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Web Scraper Customization

The scrapers in `app/services/scraper.py` are templates. You may need to:

1. Inspect newspaper HTML structure
2. Update CSS selectors
3. Handle pagination
4. Add date filtering logic

Use browser DevTools to identify correct selectors.

## Testing

Run all unit tests with verbose output (coverage report generated in `tests/coverage_report/`):

```bash
~/.pyenv/shims/pytest tests/ --ignore=tests/test_api.py -v
```

Run with coverage report:

```bash
~/.pyenv/shims/pytest tests/ --ignore=tests/test_api.py --cov=app --cov-report=html:tests/coverage_report/html --cov-report=term-missing
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── models/
│   │   ├── schemas.py       # Pydantic models
│   ├── services/
│   │   ├── openai_service.py
│   │   ├── bias_detector.py
│   │   └── scraper.py
│   ├── api/
│   │   └── routes.py
│   └── utils/
│       └── helpers.py
├── tests/
├── requirements.txt
├── .env
└── README.md
```

## License

MIT
