# Modern Telegram Scraper & Adder (2026 Swift Edition)

This repository contains a modernized, high-performance Telegram member management tool.

## Project Structure

- **/backend**: Python FastAPI engine powered by Telethon.
  - `api.py`: The core API and concurrent worker pool.
  - `telegram_member_adder.py`: CLI version and core logic.
  - `config.py`: Settings and proxy configurations.
- **/frontend** (or `tg-dashboard`): Next.js 16 Web Dashboard.
  - Luxury glassmorphism UI.
  - Real-time log streaming via WebSockets.

## Quick Start

### Backend
1. `cd backend`
2. `pip install -r requirements.txt`
3. `python api.py`

### Frontend
1. `cd frontend` (or `tg-dashboard`)
2. `npm install`
3. `npm run build`
4. `npm run start`

## Deployment
Check `backend/deployment_guide.md` (or the artifacts) for Render.com and Vercel setup instructions.