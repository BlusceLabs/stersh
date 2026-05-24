# Watch!fy

A cinematic streaming platform built with modern web technologies.

## Tech Stack

- **Frontend**: React, TanStack Router, Video.js, Framer Motion
- **Backend Gateway**: Go + Fiber
- **Extractor Service**: Python + FastAPI + Playwright
- **Styling**: Tailwind CSS + Glass Morphism

## Getting Started

1. Copy `backend/.env.example` to `backend/.env` and add your TMDB API key
2. Run `pnpm install` to install frontend dependencies
3. Run `./scripts/start.sh` to start all services

## Services

- Frontend: http://localhost:5173
- Gateway API: http://localhost:8080
- Extractor: http://localhost:8000
