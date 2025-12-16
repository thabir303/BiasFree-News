#!/bin/bash
# Quick start script for BiasFree News backend

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting BiasFree News Backend${NC}"
echo ""

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Please run this script from the backend directory"
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate venv
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Please create one with your OPENAI_API_KEY${NC}"
    echo ""
fi

# Set PYTHONPATH
export PYTHONPATH=$PWD

# Start server
echo ""
echo -e "${GREEN}✨ Starting server on http://0.0.0.0:8000${NC}"
echo -e "${GREEN}📚 API Documentation: http://localhost:8000/docs${NC}"
echo -e "${GREEN}⏰ Scheduler: Will run daily at 6:00 AM BDT${NC}"
echo ""
echo -e "${YELLOW}Press CTRL+C to stop${NC}"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
