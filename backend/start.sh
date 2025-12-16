#!/bin/bash
# Backend startup script for BiasFree News

echo "🚀 Starting BiasFree News Backend..."

# Activate virtual environment
source venv/bin/activate

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Please create it from .env.example"
    echo "   and add your OPENAI_API_KEY"
    exit 1
fi

# Start uvicorn server
echo "📡 Starting FastAPI server on http://localhost:8000"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
