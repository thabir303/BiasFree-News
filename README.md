# BiasFree News

BiasFree News is an AI-powered full-stack platform for detecting, analyzing, and reducing bias in Bengali news content.
It combines article scraping, NLP-powered bias analysis, neutral rewriting, clustering, and role-based workflows in one system.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Run the Project](#run-the-project)
- [API Overview](#api-overview)
- [Testing](#testing)
- [Deployment Notes](#deployment-notes)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

## Overview

The platform is designed to support fairer media consumption and analysis by:

- Identifying emotionally charged or politically biased language in Bengali articles
- Suggesting neutral alternatives and generating debiased content
- Recommending neutral headlines
- Aggregating and clustering similar articles from multiple newspapers
- Providing analytics, dashboards, and user-level analysis history

Live url: https://biasfree-news-chi.vercel.app

## Key Features

### Core NLP and AI

- Full pipeline processing: bias analysis, debiasing, and headline generation
- Bias score and confidence output
- Structured term-level change suggestions
- OpenAI integration with configurable model and token limits

### News Ingestion and Processing

- Manual scraping by source and date range
- Automated scheduled scraping
- Duplicate handling and article storage
- Cluster generation and unified content workflow

### User and Admin Features

- User signup and signin with JWT authentication
- Email verification and password reset with OTP
- User preferences, bookmarks, and saved analyses
- Admin-only controls for scraping, scheduler, and user management

### Product Experience

- Responsive React UI
- Protected routes for authenticated/admin views
- Article browsing, filters, and detail pages
- Cluster pages and analytics visualization

## Tech Stack

### Frontend

- React 19
- TypeScript
- Vite
- Tailwind CSS
- Axios
- MUI + chart libraries

### Backend

- FastAPI
- SQLAlchemy
- Pydantic Settings
- SlowAPI rate limiting
- APScheduler
- JWT (python-jose) + passlib

### Data and NLP

- BeautifulSoup4 + Requests + lxml (scraping)
- OpenAI API
- sentence-transformers, scikit-learn, numpy
- sumy, nltk

## System Architecture

- Frontend client sends requests to backend APIs
- Backend handles authentication, scraping, processing, and persistence
- AI services analyze and debias article text
- Database stores users, articles, analyses, bookmarks, and cluster data
- Scheduler triggers periodic scraping and processing tasks

## Project Structure

```text
bias_free/
├── backend/
│   ├── app/
│   │   ├── api/            # API routers (core, auth, enhanced)
│   │   ├── config/         # settings and newspaper configs
│   │   ├── database/       # DB setup and ORM models
│   │   ├── models/         # Pydantic schemas
│   │   ├── services/       # AI, scraping, auth, scheduler, clustering
│   │   └── utils/
│   ├── tests/              # backend test suite
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── README.md
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Git
- OpenAI API key
- SMTP credentials for email features

### 1) Clone the repository

```bash
git clone https://github.com/thabir303/BiasFree-News
cd BiasFree-News
```

### 2) Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then update .env with required values (see Environment Variables section).

### 3) Frontend setup

```bash
cd ../frontend
npm install
```

Create frontend .env file and set API base URLs:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_AUTH_BASE_URL=http://localhost:8000/auth
```

## Environment Variables

### Backend (.env)

Minimum recommended variables:

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-nano

# App
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Security
JWT_SECRET_KEY=change_this_to_a_strong_random_secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DAYS=7

# Frontend URL (for email links and CORS consistency)
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Email (required for verification and OTP flows)
MAIL_USERNAME=your_smtp_username
MAIL_PASSWORD=your_smtp_password
MAIL_FROM=your_email@example.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_FROM_NAME=BiasFree News
```

For additional optional backend settings, check backend/app/config/settings.py and backend/.env.example.

### Frontend (.env)

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_AUTH_BASE_URL=http://localhost:8000/auth
```

## Run the Project

### Start backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend docs:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Start frontend

```bash
cd frontend
npm run dev
```

Frontend (default):

- App: http://localhost:5173

## API Overview

### Authentication routes (/auth)

- POST /signup
- POST /signin
- GET /me
- POST /verify-email/{token}
- POST /forgot-password
- POST /verify-otp
- POST /reset-password

### Core and data routes (/api)

- POST /full-process
- POST /scrape/manual
- GET /articles
- GET /articles/{article_id}
- POST /articles/{article_id}/process
- GET /statistics
- GET /analytics/visualization

### Scheduler and clustering routes (/api)

- GET /scheduler/status
- POST /scheduler/update
- POST /scheduler/toggle
- GET /clusters
- GET /clusters/stats
- GET /clusters/{cluster_id}
- POST /clusters/generate

See backend docs at /docs for complete request and response schemas.

## Testing

From backend directory:

```bash
source venv/bin/activate
pytest tests/ --ignore=tests/test_api.py -v
```

Coverage run:

```bash
pytest tests/ --ignore=tests/test_api.py --cov=app --cov-report=html:tests/coverage_report/html --cov-report=term-missing
```

## Deployment Notes

- Frontend can be deployed to Vercel (already configured in current setup).
- Backend can be deployed to any Python-compatible host (for example, Render, Railway, or VPS).
- Set production-safe environment variables before deployment.
- Disable debug in production and use a strong JWT secret.

## Roadmap

- Improve multilingual support beyond Bengali
- Expand newspaper source integrations
- Add more explainable bias metrics and reports
- Introduce moderation and audit tooling for admin workflows

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes with clear messages
4. Open a pull request with a concise description

For backend and frontend module-specific notes, see:

- backend/README.md
- frontend/README.md
