# PriceHunter — Product Requirements Document

## Problem Statement
A hybrid price comparison engine for India with a chat-first UX. Conversational chatbot collects product info, makes real vendor calls via Bland.ai, discovers vendors via Google Places, simulates online prices, and ranks by intent. Monetized via Razorpay Rs 99 premium paywall.

## Architecture
- **Frontend:** React + Tailwind + Framer Motion (dark neon-green theme)
- **Backend:** FastAPI (Python, async)
- **Database:** MongoDB (analytics, payments, voice callbacks)
- **LLM:** OpenAI gpt-4o-mini via Emergent integrations
- **External APIs:** Google Places, Bland.ai, Razorpay

## Implemented Features

### Core MVP (Complete)
- [x] Query Parsing via OpenAI
- [x] Online Pipeline (simulated e-commerce)
- [x] Offline Pipeline (Google Places + Bland.ai voice calls)
- [x] Ranking Engine (cheapest/fastest/best_value/nearest)
- [x] MongoDB Analytics

### Chat-first UX (Complete)
- [x] Conversational chatbot collecting product, location, intent
- [x] Vendor list bubble (names + phone numbers)
- [x] Per-vendor progress animation
- [x] 1-minute compiling delay before results
- [x] Inline result cards with filter/sort
- [x] Quick reply chips, new search/reset

### Hybrid Offline Calling (Complete)
- [x] 1 real Bland.ai call to PANKTI SHAH (+919106812406) per search
- [x] All discovered vendors mocked
- [x] 45s timeout, graceful mock fallback on failure
- [x] Transcript extraction for real calls

### Razorpay Paywall (Complete - April 2026)
- [x] Premium upgrade popup after first search results
- [x] Rs 99 payment via Razorpay Standard Checkout (UPI, cards, netbanking)
- [x] Backend order creation (POST /api/payments/create-order)
- [x] Signature verification (POST /api/payments/verify)
- [x] Payment status tracking (GET /api/payments/status/{session_id})
- [x] MongoDB payment records (order_id, payment_id, status, timestamps)
- [x] Premium session marking — popup not shown again after payment
- [x] Dismiss behavior — close returns to chat normally

## Key Endpoints
- `POST /api/chat/message` — Main chat + search
- `POST /api/chat/reset` — Reset session
- `POST /api/payments/create-order` — Create Razorpay order
- `POST /api/payments/verify` — Verify payment signature
- `GET /api/payments/status/{session_id}` — Check premium status
- `GET /api/health` — Health check

## Backlog
- P1: Persist chat sessions + premium status in MongoDB
- P1: Fix Bland.ai 429 rate limits (real calls currently failing)
- P2: LLM top-3 recommendation summary
- P3: Real e-commerce API integrations
