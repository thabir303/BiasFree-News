# BiasFree News - Frontend

React TypeScript frontend for BiasFree News platform.

## Features

- **Article Input**: Paste Bengali news articles for analysis
- **Bias Detection**: Visual bias score with identified biased terms
- **Content Comparison**: Side-by-side original vs. debiased content
- **Headline Generation**: Neutral headline suggestions
- **Premium UI**: Dark mode with glassmorphism effects
- **Bengali Font Support**: Noto Sans Bengali

## Tech Stack

- React 19
- TypeScript
- Vite
- Tailwind CSS
- Axios

## Setup

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000/api
```

## Available Scripts

- `npm run dev` - Start development server (http://localhost:5173)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ArticleInput.tsx
│   │   └── ResultsDisplay.tsx
│   ├── services/
│   │   └── api.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json
└── package.json
```

## API Integration

Frontend connects to FastAPI backend at `http://localhost:8000/api`. Make sure backend is running before starting frontend.

## Production Build

```bash
npm run build
```

Output will be in `dist/` folder. Serve with any static file server.
