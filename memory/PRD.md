# PriceHunter — Product Requirements Document

## Problem Statement
Build a full-stack web application called PriceHunter — a hybrid price comparison engine for India. It parses natural language queries, runs an Online Pipeline (simulated e-commerce), runs an Offline Pipeline (Google Places discovery + Bland.ai voice calls to vendors), and ranks them based on intent (cheapest, fastest, best_value, nearest).

**UX Requirement (Phase 2):** Transform the app into a Chat-first UX guided shopping assistant. Replace traditional search with a conversational chatbot that collects product info, auto-triggers search, displays results inline, and shows progress states.

## Architecture
- **Frontend:** React + Tailwind + Framer Motion (dark neon-green theme)
- **Backend:** FastAPI (Python, async)
- **Database:** MongoDB (analytics, voice callbacks)
- **LLM:** OpenAI gpt-4o-mini via Emergent integrations key
- **External APIs:** Google Places API, Bland.ai voice calling (MOCKED in dev)

## Implemented Features

### Phase 1 — Core MVP (Complete)
- [x] Query Parsing via OpenAI (StructuredQuery extraction)
- [x] Online Pipeline: Simulated e-commerce results (Amazon, Flipkart, etc.)
- [x] Offline Pipeline: Google Places vendor discovery + Bland.ai voice calling (mock/real)
- [x] Ranking Engine: Intent-based scoring (cheapest, fastest, best_value, nearest)
- [x] MongoDB Analytics & Visitor Tracking
- [x] Premium dark UI with glassmorphism

### Phase 2 — Chat-first UX (Complete - April 2026)
- [x] Conversational chat UI with user/assistant message bubbles
- [x] LLM-powered shopping assistant that collects product, location, intent
- [x] Auto-trigger search when enough context gathered
- [x] Inline results display with rank badges, filter (all/online/offline), sort (rank/price/speed)
- [x] Search progress timeline (6 stages with live status)
- [x] Quick reply chips for example queries
- [x] New Search / reset functionality
- [x] POST /api/chat/message — session-based conversational endpoint
- [x] POST /api/chat/reset — reset chat session

## Key Endpoints
- `POST /api/chat/message` — Main chat endpoint (session, message → assistant response + optional results)
- `POST /api/chat/reset` — Reset chat session
- `POST /api/search` — Legacy search endpoint (still functional)
- `GET /api/health` — Health check
- `GET /api/stats` — Analytics

## Backlog / Future Tasks
- P1: Persist chat sessions in MongoDB (currently in-memory)
- P1: Real Bland.ai call stability (rate limit retry, circuit breaker)
- P2: LLM top-3 recommendation summary as final chat message
- P2: Persistent chat history (resume sessions)
- P2: User accounts / saved searches
- P3: Real e-commerce API integrations (replace simulated data)

## Known Limitations
- Voice calls MOCKED (MOCK_VOICE_CALLS=true) — real Bland.ai calls cause 502 timeouts
- Online pipeline results are simulated, not real API data
- Chat sessions are in-memory (lost on restart)
