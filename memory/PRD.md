# PriceHunter — Product Requirements Document

## Problem Statement
Build a full-stack web application called PriceHunter — a hybrid price comparison engine for India. It parses natural language queries, runs an Online Pipeline (simulated e-commerce), runs an Offline Pipeline (Google Places discovery + Bland.ai voice calls to vendors), and ranks them based on intent (cheapest, fastest, best_value, nearest).

**UX Requirement (Phase 2):** Transform the app into a Chat-first UX guided shopping assistant with staged display flow:
1. Chat collects product info through conversation
2. Shows discovered vendor names + phone numbers
3. Shows live progress animation (contacting each vendor)
4. 1-minute delay (compiling results)
5. Shows all result cards (online + offline combined)

## Architecture
- **Frontend:** React + Tailwind + Framer Motion (dark neon-green theme)
- **Backend:** FastAPI (Python, async)
- **Database:** MongoDB (analytics, voice callbacks)
- **LLM:** OpenAI gpt-4o-mini via Emergent integrations key
- **External APIs:** Google Places API, Bland.ai voice calling (MOCKED in dev)

## Implemented Features

### Phase 1 — Core MVP (Complete)
- [x] Query Parsing via OpenAI (StructuredQuery extraction)
- [x] Online Pipeline: Simulated e-commerce results
- [x] Offline Pipeline: Google Places vendor discovery + Bland.ai voice calling (mock/real)
- [x] Ranking Engine: Intent-based scoring
- [x] MongoDB Analytics

### Phase 2 — Chat-first UX with Staged Display (Complete - April 2026)
- [x] Conversational chat UI with user/assistant message bubbles
- [x] LLM-powered shopping assistant collecting product, location, intent
- [x] Auto-trigger search when enough context gathered
- [x] Vendor list chat bubble (names + phone numbers)
- [x] Per-vendor progress animation ("Contacting X...")
- [x] 1-minute delay after progress before results (compiling state)
- [x] Inline result cards with rank/price/vendor/source/delivery/availability/confidence
- [x] Filter & sort controls, search summary timeline
- [x] Quick reply chips, new search/reset

## Key Endpoints
- `POST /api/chat/message` — Chat endpoint (returns discovered_vendors, progress_states, results)
- `POST /api/chat/reset` — Reset chat session
- `POST /api/search` — Legacy search endpoint
- `GET /api/health` — Health check

## Backlog / Future Tasks
- P1: Persist chat sessions in MongoDB (currently in-memory)
- P1: Real Bland.ai call stability
- P2: LLM top-3 recommendation summary
- P2: Persistent chat history
- P3: Real e-commerce API integrations

## Known Limitations
- Voice calls MOCKED (MOCK_VOICE_CALLS=true)
- Online pipeline results simulated
- Chat sessions in-memory (lost on restart)
