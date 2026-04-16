# PriceHunter — Product Requirements Document

## Problem Statement
Build a full-stack web application called PriceHunter — a hybrid price comparison engine for India. It parses natural language queries, runs an Online Pipeline (simulated e-commerce), runs an Offline Pipeline (Google Places discovery + Bland.ai voice calls to vendors), and ranks them based on intent (cheapest, fastest, best_value, nearest).

**UX Requirement:** Chat-first UX guided shopping assistant with staged display flow.

## Architecture
- **Frontend:** React + Tailwind + Framer Motion (dark neon-green theme)
- **Backend:** FastAPI (Python, async)
- **Database:** MongoDB (analytics, voice callbacks)
- **LLM:** OpenAI gpt-4o-mini via Emergent integrations key
- **External APIs:** Google Places API, Bland.ai voice calling

## Implemented Features

### Phase 1 — Core MVP (Complete)
- [x] Query Parsing via OpenAI (StructuredQuery extraction)
- [x] Online Pipeline: Simulated e-commerce results
- [x] Offline Pipeline: Google Places vendor discovery
- [x] Ranking Engine: Intent-based scoring
- [x] MongoDB Analytics

### Phase 2 — Chat-first UX (Complete - April 2026)
- [x] Conversational chat UI with user/assistant message bubbles
- [x] LLM-powered shopping assistant collecting product, location, intent
- [x] Auto-trigger search when enough context gathered
- [x] Vendor list chat bubble (names + phone numbers, includes PANKTI SHAH)
- [x] Per-vendor progress animation ("Calling/Contacting X...")
- [x] 1-minute delay after progress before results (compiling state)
- [x] Inline result cards with rank/price/vendor/source/delivery/availability/confidence
- [x] Filter & sort controls, search summary timeline

### Phase 3 — Hybrid 2-Call Offline Pipeline (Complete - April 2026)
- [x] Exactly 2 real Bland.ai calls per search:
  - Call #1: PANKTI SHAH at +919106812406 (fixed target)
  - Call #2: Top discovered vendor from Google Places
- [x] All other vendors use mocked results
- [x] Sequential calls, 45s timeout per call, 5s delay between
- [x] Graceful fallback to mock on failure/timeout/rate-limit
- [x] Real transcript extraction (price, availability, negotiated, delivery)
- [x] Detailed logging (start/end, transcript, extracted data, fallback)
- [x] MOCK_VOICE_CALLS=false (real calls enabled)
- [x] App never crashes on call failure

## Key Endpoints
- `POST /api/chat/message` — Chat endpoint (discovered_vendors, progress_states, results)
- `POST /api/chat/reset` — Reset chat session
- `POST /api/search` — Legacy search endpoint
- `GET /api/health` — Health check

## Known Limitations
- Bland.ai rate limits may cause 429 errors — falls back to mock gracefully
- Online pipeline results are simulated
- Chat sessions in-memory (lost on restart)

## Backlog
- P1: Persist chat sessions in MongoDB
- P2: LLM top-3 recommendation summary
- P2: Persistent chat history
- P3: Real e-commerce API integrations
