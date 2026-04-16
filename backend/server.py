from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import hmac
import hashlib
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Any
import uuid
import json
from datetime import datetime, timezone
import asyncio
import random
from emergentintegrations.llm.chat import LlmChat, UserMessage
import googlemaps
import phonenumbers
import razorpay
from online_pipeline import run_online_pipeline, UnifiedResult
from vendor_discovery import discover_vendors, Vendor
from voice_calling import call_vendors_for_pricing, CallResult
from ranking_engine import rank_results

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Google Places API client
google_places_key = os.environ.get('GOOGLE_PLACES_API_KEY')
gmaps = googlemaps.Client(key=google_places_key) if google_places_key else None

# Voice calling configuration
BLAND_API_KEY = os.environ.get('BLAND_API_KEY')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
MOCK_VOICE_CALLS = os.environ.get('MOCK_VOICE_CALLS', 'true').lower() == 'true'

# Razorpay configuration
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    logger.info("Razorpay client initialized")
else:
    logger.warning("Razorpay keys not configured")

# Pydantic Models
class SearchRequest(BaseModel):
    query: str
    location: Optional[str] = None

class StructuredQuery(BaseModel):
    product: str
    category: Literal["groceries", "electronics", "clothing", "medicine", "hardware", "general"]
    location: str
    intent: Literal["cheapest", "fastest", "best_value", "nearest"]
    raw_query: str

class SearchResult(BaseModel):
    id: str
    rank: int
    source_type: Literal["ONLINE", "OFFLINE"]
    vendor_name: str
    price: float
    delivery_time: str
    confidence: float
    is_best_deal: bool
    product_name: str
    category: str
    availability: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    online_count: int
    offline_count: int
    search_time: float
    parsed_query: StructuredQuery

# Chat models
class ChatMessageRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class ProgressState(BaseModel):
    stage: str
    status: str  # "pending", "active", "completed", "failed"
    detail: Optional[str] = None

class ChatMessageResponse(BaseModel):
    session_id: str
    assistant_message: str
    conversation_state: str  # "collecting", "searching", "results_ready"
    search_triggered: bool
    results: Optional[List[dict]] = None
    search_metadata: Optional[dict] = None
    progress_states: List[dict] = []
    parsed_query: Optional[dict] = None


def unified_to_search_result(unified: UnifiedResult, product: str, category: str) -> dict:
    """Convert UnifiedResult to SearchResult dict format"""
    return {
        "source_type": "ONLINE" if unified.source_type == "online" else "OFFLINE",
        "vendor_name": unified.name,
        "price": unified.price,
        "delivery_time": unified.delivery_time,
        "confidence": unified.confidence,
        "product_name": product,
        "category": category,
        "availability": "In Stock" if unified.availability else "Out of Stock"
    }


CHAT_SYSTEM_PROMPT = """You are PriceHunter's shopping assistant. You help users find the best prices for products in India by collecting their requirements through friendly conversation.

Your job:
1. Greet the user warmly and ask what they're looking for.
2. Through natural conversation, collect:
   - **product**: The specific product or item they want (REQUIRED)
   - **location**: Their city or area in India (REQUIRED - ask if not provided)
   - **intent**: What matters most - cheapest price, fastest delivery, best overall value, or nearest shop (OPTIONAL - default to "best_value")
3. Be conversational, friendly, and brief. Use 1-2 sentences max per response.
4. Do NOT ask unnecessary follow-up questions. If the user names a product and location, that's enough — trigger the search immediately.
5. Only ask a clarifying question if the product is truly ambiguous (e.g., "something for my kitchen") or if location is missing.

CRITICAL RULE:
When you have at least the product AND location, you MUST trigger the search. End your message with a special trigger on a NEW LINE:
[SEARCH_READY]{"product":"<product>","category":"<category>","location":"<location>","intent":"<intent>"}

The category must be one of: groceries, electronics, clothing, medicine, hardware, general
The intent must be one of: cheapest, fastest, best_value, nearest

Examples:
- "cheapest iPhone 15 in Bangalore" → trigger immediately (product=iPhone 15, location=Bangalore, intent=cheapest)
- "tomatoes near Rajkot" → trigger immediately (product=tomatoes, location=Rajkot, intent=nearest)
- "I need a laptop" → ask for location only, then trigger
- "help me find something" → ask what product they need

IMPORTANT:
- Do NOT ask about model variants, colors, or storage unless truly ambiguous.
- If the user provides product + location in one message, respond briefly and trigger.
- The JSON after [SEARCH_READY] must be valid JSON on the same line as the tag.
"""


# In-memory session store for chat conversations
chat_sessions = {}


async def get_chat_session(session_id: str) -> dict:
    """Get or create a chat session"""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = {
            "session_id": session_id,
            "messages": [],
            "state": "collecting",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    return chat_sessions[session_id]


@api_router.post("/chat/message")
async def chat_message(request: ChatMessageRequest):
    """
    Chat endpoint for conversational shopping assistant.
    Collects product info through conversation, triggers search when ready.
    """
    session_id = request.session_id or str(uuid.uuid4())
    user_msg = request.message.strip()

    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session = await get_chat_session(session_id)

    # Add user message to history
    session["messages"].append({"role": "user", "content": user_msg})

    # Build conversation history for LLM
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM API key not configured")

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"pricehunter_chat_{session_id}",
            system_message=CHAT_SYSTEM_PROMPT
        ).with_model("openai", "gpt-4o-mini")

        # Replay previous messages to maintain context
        for msg in session["messages"]:
            if msg["role"] == "user":
                await chat.send_message(UserMessage(text=msg["content"]))
            # Note: assistant messages are part of the LlmChat session automatically

        # Actually we need a different approach - send all history as context
        # Let's rebuild: send the full conversation as a single contextual message
    except Exception as e:
        logger.error(f"Chat LLM error: {e}")

    # Better approach: single LLM call with full conversation context
    try:
        conversation_text = ""
        for msg in session["messages"][:-1]:  # All messages except current
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n"

        prompt = conversation_text + f"User: {user_msg}"

        chat = LlmChat(
            api_key=api_key,
            session_id=str(uuid.uuid4()),
            system_message=CHAT_SYSTEM_PROMPT
        ).with_model("openai", "gpt-4o-mini")

        assistant_response = await chat.send_message(UserMessage(text=prompt))
        assistant_response = assistant_response.strip()

    except Exception as e:
        logger.error(f"Chat LLM error: {e}", exc_info=True)
        assistant_response = "I'm having trouble understanding. Could you tell me what product you're looking for and your city?"

    # Check if search should be triggered
    search_triggered = False
    results = None
    search_metadata = None
    progress_states = []
    parsed_query_dict = None
    discovered_vendors = []
    display_message = assistant_response

    if "[SEARCH_READY]" in assistant_response:
        search_triggered = True
        session["state"] = "searching"

        # Extract the JSON from the response
        parts = assistant_response.split("[SEARCH_READY]")
        display_message = parts[0].strip()
        json_str = parts[1].strip() if len(parts) > 1 else ""

        # Parse the structured query
        try:
            search_params = json.loads(json_str)
            product = search_params.get("product", user_msg)
            category = search_params.get("category", "general")
            location = search_params.get("location", "India")
            intent = search_params.get("intent", "best_value")

            # Validate category and intent
            valid_categories = ["groceries", "electronics", "clothing", "medicine", "hardware", "general"]
            valid_intents = ["cheapest", "fastest", "best_value", "nearest"]
            if category not in valid_categories:
                category = "general"
            if intent not in valid_intents:
                intent = "best_value"

            structured_query = StructuredQuery(
                product=product,
                category=category,
                location=location,
                intent=intent,
                raw_query=user_msg
            )
            parsed_query_dict = structured_query.model_dump()

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse search params: {e}")
            structured_query = await parse_query_with_openai(user_msg, None)
            parsed_query_dict = structured_query.model_dump()

        # Step 1: Discover vendors first (for the vendor list chat message)
        try:
            raw_vendors = await discover_local_vendors_with_google_places(
                structured_query.product,
                structured_query.category,
                structured_query.location
            )
            for v in raw_vendors:
                discovered_vendors.append({
                    "name": v.get("name", "Unknown"),
                    "phone": v.get("phone_number", "N/A"),
                    "address": v.get("address", ""),
                })
            logger.info(f"Discovered {len(discovered_vendors)} vendors for chat display")
        except Exception as e:
            logger.error(f"Vendor discovery for chat failed: {e}")

        # Build progress states — PANKTI SHAH real call + discovered vendors mocked
        progress_states = [
            {"stage": "Understanding your request", "status": "completed", "detail": f"Looking for {structured_query.product} in {structured_query.location}"},
            {"stage": "Searching online platforms", "status": "pending", "detail": "Checking Amazon, Flipkart, and more..."},
            {"stage": "Calling PANKTI SHAH", "status": "pending", "detail": "+919106812406 (live call)"},
        ]
        for v in discovered_vendors:
            progress_states.append({
                "stage": f"Contacting {v['name']}",
                "status": "pending",
                "detail": v.get("phone", ""),
            })
        progress_states.append({"stage": "Negotiating best deals", "status": "pending", "detail": None})
        progress_states.append({"stage": "Comparing & ranking all results", "status": "pending", "detail": None})

        # Add PANKTI SHAH to discovered_vendors for frontend display
        discovered_vendors.insert(0, {
            "name": "PANKTI SHAH",
            "phone": "+919106812406",
            "address": "Direct contact",
        })

        # Step 2: Run the actual search
        try:
            start_time = asyncio.get_event_loop().time()

            online_results = []
            offline_results = []

            # Online pipeline
            try:
                online_unified = await run_online_pipeline(
                    structured_query.product,
                    structured_query.category,
                    structured_query.location
                )
                online_results = [
                    unified_to_search_result(r, structured_query.product, structured_query.category)
                    for r in online_unified
                ]
                progress_states[1]["status"] = "completed"
                progress_states[1]["detail"] = f"Found {len(online_results)} online results"
            except Exception as e:
                logger.error(f"Online pipeline failed: {e}")
                progress_states[1]["status"] = "failed"
                progress_states[1]["detail"] = "Online search encountered an error"

            # Offline pipeline
            try:
                offline_results = await run_offline_pipeline_safe(
                    structured_query.product,
                    structured_query.category,
                    structured_query.location
                )
                # Mark all vendor contact stages as completed
                for i in range(2, 2 + len(discovered_vendors)):
                    if i < len(progress_states) - 2:
                        progress_states[i]["status"] = "completed"
                # Negotiating
                progress_states[-2]["status"] = "completed"
                progress_states[-2]["detail"] = f"Got prices from {len(offline_results)} vendors"
            except Exception as e:
                logger.error(f"Offline pipeline failed: {e}")
                for i in range(2, 2 + len(discovered_vendors)):
                    if i < len(progress_states) - 2:
                        progress_states[i]["status"] = "failed"

            # Combine and rank
            all_results = online_results + offline_results

            if all_results:
                ranked = rank_results(all_results, structured_query.intent)
                results_list = []
                for r in ranked:
                    results_list.append({
                        "id": str(uuid.uuid4()),
                        "rank": r["rank"],
                        "source_type": r["source_type"],
                        "vendor_name": r["vendor_name"],
                        "price": r["price"],
                        "delivery_time": r["delivery_time"],
                        "confidence": r["confidence"],
                        "is_best_deal": r["rank"] == 1,
                        "product_name": r["product_name"],
                        "category": r["category"],
                        "availability": r["availability"],
                        "negotiated": r.get("negotiated", False),
                        "notes": r.get("notes", ""),
                        "score": r.get("score", 0),
                    })
                results = results_list
                progress_states[-1]["status"] = "completed"
                progress_states[-1]["detail"] = f"Ranked {len(results)} results by {structured_query.intent}"
            else:
                progress_states[-1]["status"] = "failed"
                progress_states[-1]["detail"] = "No results found"

            end_time = asyncio.get_event_loop().time()
            search_time = round(end_time - start_time, 2)

            search_metadata = {
                "total_results": len(results) if results else 0,
                "online_count": len(online_results),
                "offline_count": len(offline_results),
                "search_time": search_time,
                "intent": structured_query.intent,
            }

            session["state"] = "results_ready"

            # Store analytics
            try:
                await store_search_analytics(
                    query=structured_query.raw_query,
                    location=structured_query.location,
                    structured_query=structured_query,
                    results_count=len(results) if results else 0,
                    search_time=search_time
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Search execution error: {e}", exc_info=True)
            display_message += "\n\nI encountered an error while searching. Please try again."
            session["state"] = "collecting"

    # Store assistant message
    session["messages"].append({"role": "assistant", "content": display_message})

    return {
        "session_id": session_id,
        "assistant_message": display_message,
        "conversation_state": session["state"],
        "search_triggered": search_triggered,
        "discovered_vendors": discovered_vendors,
        "results": results,
        "search_metadata": search_metadata,
        "progress_states": progress_states,
        "parsed_query": parsed_query_dict,
    }


@api_router.post("/chat/reset")
async def reset_chat(request: dict):
    """Reset a chat session"""
    session_id = request.get("session_id")
    if session_id and session_id in chat_sessions:
        del chat_sessions[session_id]
    return {"status": "ok", "message": "Session reset"}


# ── Razorpay Payment Endpoints ──

class CreateOrderRequest(BaseModel):
    session_id: Optional[str] = None

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    session_id: Optional[str] = None


@api_router.post("/payments/create-order")
async def create_razorpay_order(request: CreateOrderRequest):
    """Create a Razorpay order for Rs 99 premium upgrade"""
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment service not configured")

    try:
        order_data = {
            "amount": 9900,  # Rs 99 in paise
            "currency": "INR",
            "receipt": f"ph_{uuid.uuid4().hex[:16]}",
            "payment_capture": 1,
        }

        order = razorpay_client.order.create(data=order_data)
        logger.info(f"Razorpay order created: {order['id']} for Rs 99")

        # Store order in DB
        payments_collection = db["payments"]
        await payments_collection.insert_one({
            "order_id": order["id"],
            "session_id": request.session_id,
            "amount": 9900,
            "currency": "INR",
            "status": "created",
            "created_at": datetime.now(timezone.utc),
        })

        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": RAZORPAY_KEY_ID,
        }

    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create payment order")


@api_router.post("/payments/verify")
async def verify_razorpay_payment(request: VerifyPaymentRequest):
    """Verify Razorpay payment signature and mark as paid"""
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment service not configured")

    try:
        # Verify signature
        message = f"{request.razorpay_order_id}|{request.razorpay_payment_id}"
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if generated_signature != request.razorpay_signature:
            logger.warning(f"Payment signature mismatch for order {request.razorpay_order_id}")
            raise HTTPException(status_code=400, detail="Payment verification failed")

        logger.info(f"Payment verified: order={request.razorpay_order_id} payment={request.razorpay_payment_id}")

        # Update payment record in DB
        payments_collection = db["payments"]
        await payments_collection.update_one(
            {"order_id": request.razorpay_order_id},
            {"$set": {
                "payment_id": request.razorpay_payment_id,
                "signature": request.razorpay_signature,
                "status": "paid",
                "paid_at": datetime.now(timezone.utc),
                "session_id": request.session_id,
            }}
        )

        return {
            "status": "paid",
            "order_id": request.razorpay_order_id,
            "payment_id": request.razorpay_payment_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Payment verification failed")


@api_router.get("/payments/status/{session_id}")
async def check_payment_status(session_id: str):
    """Check if a session has an active premium payment"""
    payments_collection = db["payments"]
    payment = await payments_collection.find_one(
        {"session_id": session_id, "status": "paid"},
        {"_id": 0, "order_id": 1, "payment_id": 1, "status": 1, "paid_at": 1}
    )
    if payment:
        if payment.get("paid_at"):
            payment["paid_at"] = payment["paid_at"].isoformat()
        return {"is_premium": True, "payment": payment}
    return {"is_premium": False}


def generate_mock_offline_results(product: str, category: str, location: str, count: int = 3) -> List[dict]:
    """Generate mock offline vendor results (simulating Bland.ai calls)"""
    results = []
    base_price = random.randint(1000, 50000) if category.lower() in ["electronics", "phone", "laptop"] else random.randint(50, 5000)
    
    for i in range(count):
        vendor = random.choice([
            "Sharma Electronics", "Kumar Store", "Patel Traders",
            "Singh Mart", "Gupta Super Market", "Reddy Shopping Center",
            "Mehta Electronics", "Desai General Store", "Joshi Bazaar",
            "Rao Provisions"
        ])
        price_variation = random.uniform(0.80, 1.10)  # Offline can be cheaper or slightly more
        price = round(base_price * price_variation, 2)
        
        delivery_options = [
            "Pick up now",
            "Local delivery (1-2 hours)",
            "Same day delivery",
            "Pick up in 30 mins"
        ]
        
        availability_options = ["In Stock", "In Stock", "Limited Stock", "Call to confirm"]
        
        results.append({
            "source_type": "OFFLINE",
            "vendor_name": f"{vendor} ({location})",
            "price": price,
            "delivery_time": random.choice(delivery_options),
            "confidence": random.uniform(0.70, 0.95),
            "product_name": product,
            "category": category,
            "availability": random.choice(availability_options)
        })
    
    return results

async def discover_local_vendors_with_google_places(product: str, category: str, location: str) -> List[dict]:
    """Discover local vendors using enhanced vendor discovery service"""
    if not location or location.lower() == "unknown":
        logger.info("No valid location, using mock vendors")
        vendors = discover_vendors(category, "India", gmaps, max_results=5)
    else:
        logger.info(f"Discovering vendors for {category} near {location}")
        vendors = discover_vendors(category, location, gmaps, max_results=10)
    
    # Convert Vendor objects to dict format
    vendor_dicts = []
    for vendor in vendors:
        vendor_dicts.append({
            "name": vendor.name,
            "phone_number": vendor.phone,
            "address": vendor.address,
            "place_id": vendor.place_id,
            "location": vendor.location,
            "rating": vendor.rating,
            "is_mock": vendor.is_mock
        })
    
    logger.info(f"Discovered {len(vendor_dicts)} vendors ({sum(1 for v in vendors if not v.is_mock)} real, {sum(1 for v in vendors if v.is_mock)} mock)")
    return vendor_dicts

async def call_vendors_with_ai(vendors: List[dict], product: str, category: str) -> List[dict]:
    """
    Call vendors using AI voice calling (Bland.ai) or mock mode
    Returns list of results with pricing and availability
    """
    if not vendors:
        logger.info("No vendors to call")
        return []
    
    logger.info(f"Calling {len(vendors)} vendors (MOCK_MODE={MOCK_VOICE_CALLS})")
    
    # Call all vendors concurrently using voice calling service
    call_results = await call_vendors_for_pricing(
        vendors=vendors,
        product=product,
        category=category,
        bland_api_key=BLAND_API_KEY,
        openai_api_key=EMERGENT_LLM_KEY,
        mock_mode=MOCK_VOICE_CALLS
    )
    
    # Convert CallResult to dict format for search results
    results = []
    for call_result in call_results:
        if call_result.price and call_result.availability:
            results.append({
                "source_type": "OFFLINE",
                "vendor_name": call_result.vendor_name,
                "price": call_result.price,
                "delivery_time": call_result.delivery_time or "Contact vendor",
                "confidence": call_result.confidence,
                "product_name": product,
                "category": category,
                "availability": "In Stock" if call_result.availability else "Out of Stock"
            })
            logger.info(
                f"✓ {call_result.vendor_name}: ₹{call_result.price} "
                f"({'negotiated' if call_result.negotiated else 'fixed'})"
            )
        else:
            logger.info(f"✗ {call_result.vendor_name}: No price/unavailable")
    
    logger.info(f"Successfully got pricing from {len(results)}/{len(call_results)} calls")
    return results

async def parse_query_with_openai(query: str, location: Optional[str]) -> StructuredQuery:
    """Parse user query using OpenAI to extract product, category, location, and intent with retry logic"""
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    
    system_message = """You are a query structuring assistant. Convert the user's natural language shopping query into a structured JSON object. Return ONLY valid JSON with these fields:
- product: the specific item (string)
- category: one of groceries, electronics, clothing, medicine, hardware, general (string)
- location: city or area mentioned, or unknown (string)
- intent: one of cheapest, fastest, best_value, nearest — infer from context (string)
- raw_query: the original query verbatim (string)

Examples:
Query: "cheap tomatoes in Rajkot"
{"product": "tomatoes", "category": "groceries", "location": "Rajkot", "intent": "cheapest", "raw_query": "cheap tomatoes in Rajkot"}

Query: "fastest delivery iPhone 15 Bangalore"
{"product": "iPhone 15", "category": "electronics", "location": "Bangalore", "intent": "fastest", "raw_query": "fastest delivery iPhone 15 Bangalore"}

Return ONLY the JSON object, no additional text."""
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=str(uuid.uuid4()),
                system_message=system_message
            ).with_model("openai", "gpt-4o-mini")
            
            user_message = UserMessage(
                text=f"Query: {query}\nProvided Location Parameter: {location or 'Not provided'}"
            )
            
            response = await chat.send_message(user_message)
            
            # Parse the JSON response
            import json
            parsed = json.loads(response.strip())
            
            # Override location if explicitly provided
            if location:
                parsed['location'] = location
            
            # Ensure raw_query is set
            if 'raw_query' not in parsed:
                parsed['raw_query'] = query
            
            # Create and validate StructuredQuery
            structured_query = StructuredQuery(**parsed)
            
            logger.info(f"Successfully parsed query (attempt {attempt + 1}): {structured_query.model_dump()}")
            return structured_query
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                # Last attempt failed, use fallback
                logger.error("All parsing attempts failed, using fallback")
                break
        except Exception as e:
            logger.error(f"Error parsing query with OpenAI (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                break
    
    # Fallback: Use raw query as product name
    logger.info("Using fallback parsing")
    return StructuredQuery(
        product=query,
        category="general",
        location=location or "unknown",
        intent="cheapest",
        raw_query=query
    )

@api_router.post("/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """Main search endpoint that processes queries and returns ranked results"""
    start_time = asyncio.get_event_loop().time()
    
    # Extract visitor tracking info from headers
    from fastapi import Request as FastAPIRequest
    from starlette.requests import Request as StarletteRequest
    
    try:
        # Step 1: Parse query with OpenAI (with retry and fallback)
        structured_query = await parse_query_with_openai(request.query, request.location)
        
        # Step 2: Run online and offline pipelines IN PARALLEL
        logger.info("Running online and offline pipelines concurrently")
        
        # Create tasks for parallel execution
        online_task = asyncio.create_task(
            run_online_pipeline(
                structured_query.product,
                structured_query.category,
                structured_query.location
            )
        )
        
        offline_task = asyncio.create_task(
            run_offline_pipeline_safe(
                structured_query.product,
                structured_query.category,
                structured_query.location
            )
        )
        
        # Wait for both pipelines (continue even if one fails)
        online_results = []
        offline_results = []
        
        try:
            online_unified_results = await online_task
            online_results = [
                unified_to_search_result(r, structured_query.product, structured_query.category)
                for r in online_unified_results
            ]
            logger.info(f"✓ Online pipeline: {len(online_results)} results")
        except Exception as e:
            logger.error(f"✗ Online pipeline failed: {e}", exc_info=True)
        
        try:
            offline_results = await offline_task
            logger.info(f"✓ Offline pipeline: {len(offline_results)} results")
        except Exception as e:
            logger.error(f"✗ Offline pipeline failed: {e}", exc_info=True)
        
        # Step 3: Combine and rank results using intelligent scoring
        all_results = online_results + offline_results
        
        if not all_results:
            raise HTTPException(
                status_code=500,
                detail="Both pipelines failed. Please try again."
            )
        
        logger.info(f"Ranking {len(all_results)} results by intent: {structured_query.intent}")
        ranked_results = rank_results(all_results, structured_query.intent)
        
        # Step 4: Create SearchResult objects
        search_results = []
        for result in ranked_results:
            search_results.append(SearchResult(
                id=str(uuid.uuid4()),
                rank=result["rank"],
                is_best_deal=(result["rank"] == 1),
                source_type=result["source_type"],
                vendor_name=result["vendor_name"],
                price=result["price"],
                delivery_time=result["delivery_time"],
                confidence=result["confidence"],
                product_name=result["product_name"],
                category=result["category"],
                availability=result["availability"]
            ))
        
        end_time = asyncio.get_event_loop().time()
        search_time = round(end_time - start_time, 2)
        
        # Step 5: Store search in MongoDB analytics
        try:
            await store_search_analytics(
                query=request.query,
                location=request.location,
                structured_query=structured_query,
                results_count=len(search_results),
                search_time=search_time
            )
        except Exception as e:
            logger.error(f"Failed to store analytics: {e}")
        
        # Step 6: Return response
        response = SearchResponse(
            results=search_results,
            total_results=len(search_results),
            online_count=len(online_results),
            offline_count=len(offline_results),
            search_time=search_time,
            parsed_query=structured_query
        )
        
        logger.info(
            f"Search complete: {len(search_results)} results in {search_time}s "
            f"({len(online_results)} online, {len(offline_results)} offline)"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Critical error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def run_offline_pipeline_safe(product: str, category: str, location: str) -> List[dict]:
    """
    HYBRID OFFLINE PIPELINE — 1 real call + all others mocked:
    - Make 1 real Bland.ai call to PANKTI SHAH (+919106812406)
    - Mock ALL discovered Google Places vendors
    - Wait for real call to complete or timeout before returning
    - Use transcript-derived data from real call
    - Fallback to mock if real call fails
    """
    from voice_calling import VoiceCallingService

    # ── Configuration ──
    ALWAYS_CALL_NAME = "PANKTI SHAH"
    ALWAYS_CALL_PHONE = "+919106812406"
    REAL_CALL_TIMEOUT = 45  # seconds max wait

    logger.info("=" * 70)
    logger.info("OFFLINE PIPELINE: 1 REAL CALL + ALL OTHERS MOCKED")
    logger.info(f"  Product: {product} | Category: {category} | Location: {location}")
    logger.info(f"  Real call target: {ALWAYS_CALL_NAME} ({ALWAYS_CALL_PHONE})")
    logger.info(f"  Timeout: {REAL_CALL_TIMEOUT}s")
    logger.info("=" * 70)

    # ── Step 1: Discover vendors via Google Places ──
    discovered_vendors = []
    try:
        discovered_vendors = await discover_local_vendors_with_google_places(
            product, category, location
        )
        logger.info(f"Discovered {len(discovered_vendors)} vendors from Google Places")
    except Exception as e:
        logger.error(f"Vendor discovery failed: {e}")

    # ── Step 2: Real call to PANKTI SHAH ──
    voice_service = VoiceCallingService(
        bland_api_key=BLAND_API_KEY,
        openai_api_key=EMERGENT_LLM_KEY,
        mock_mode=False
    )
    mock_service = VoiceCallingService(
        bland_api_key=BLAND_API_KEY,
        openai_api_key=EMERGENT_LLM_KEY,
        mock_mode=True
    )

    pankti_result = None
    real_call_success = False

    logger.info("-" * 50)
    logger.info(f"REAL CALL: {ALWAYS_CALL_NAME} ({ALWAYS_CALL_PHONE})")
    logger.info(f"  Starting call... (timeout: {REAL_CALL_TIMEOUT}s)")

    try:
        call_result = await voice_service.call_vendor(
            vendor_name=ALWAYS_CALL_NAME,
            vendor_phone=ALWAYS_CALL_PHONE,
            product=product,
            category=category,
            max_wait=REAL_CALL_TIMEOUT
        )

        if call_result.status == "completed" and call_result.price is not None:
            logger.info(f"  CALL COMPLETED — {ALWAYS_CALL_NAME}")
            logger.info(f"    Call ID: {call_result.call_id}")
            logger.info(f"    Transcript: {(call_result.transcript or '')[:200]}...")
            logger.info(f"    Price: {call_result.price}")
            logger.info(f"    Availability: {call_result.availability}")
            logger.info(f"    Negotiated: {call_result.negotiated}")
            logger.info(f"    Delivery: {call_result.delivery_time}")
            logger.info(f"    Confidence: {call_result.confidence}")
            logger.info(f"    Notes: {call_result.notes}")

            pankti_result = {
                "source_type": "OFFLINE",
                "vendor_name": call_result.vendor_name,
                "price": call_result.price,
                "delivery_time": call_result.delivery_time or "Contact vendor",
                "confidence": call_result.confidence,
                "product_name": product,
                "category": category,
                "availability": "In Stock" if call_result.availability else "Out of Stock",
                "negotiated": call_result.negotiated,
                "notes": call_result.notes,
            }
            real_call_success = True
        else:
            logger.warning(f"  CALL FAILED/INCOMPLETE — {ALWAYS_CALL_NAME} (status: {call_result.status})")
            logger.warning(f"    Transcript: {call_result.transcript}")
            logger.warning(f"    Falling back to mock for {ALWAYS_CALL_NAME}")
    except Exception as e:
        logger.error(f"  EXCEPTION during call to {ALWAYS_CALL_NAME}: {e}")
        logger.error(f"    Falling back to mock for {ALWAYS_CALL_NAME}")

    # Fallback to mock if real call failed
    if not real_call_success:
        mock_result = await mock_service.call_vendor(
            vendor_name=ALWAYS_CALL_NAME,
            vendor_phone=ALWAYS_CALL_PHONE,
            product=product,
            category=category
        )
        pankti_result = {
            "source_type": "OFFLINE",
            "vendor_name": mock_result.vendor_name,
            "price": mock_result.price,
            "delivery_time": mock_result.delivery_time or "Contact vendor",
            "confidence": mock_result.confidence * 0.8,
            "product_name": product,
            "category": category,
            "availability": "In Stock" if mock_result.availability else "Out of Stock",
            "negotiated": mock_result.negotiated,
            "notes": "MOCK FALLBACK — real call failed",
        }

    # ── Step 3: Mock ALL discovered vendors ──
    mock_results = []
    for vendor in discovered_vendors:
        base_price = random.randint(5000, 150000) if category == "electronics" else random.randint(50, 5000)
        price = round(base_price * random.uniform(0.8, 1.1), 2)
        mock_results.append({
            "source_type": "OFFLINE",
            "vendor_name": vendor["name"],
            "price": price,
            "delivery_time": random.choice([
                "Pick up now", "Local delivery (1-2 hours)",
                "Same day delivery", "Available in 30 mins"
            ]),
            "confidence": random.uniform(0.7, 0.9),
            "product_name": product,
            "category": category,
            "availability": random.choice(["In Stock", "Available", "Limited Stock"]),
            "negotiated": False,
            "notes": "",
        })
    logger.info(f"Generated mock data for {len(mock_results)} discovered vendors")

    # ── Step 4: Combine ──
    all_offline_results = [pankti_result] + mock_results

    if len(all_offline_results) < 3:
        generic_mock = generate_mock_offline_results(
            product, category, location,
            count=3 - len(all_offline_results)
        )
        all_offline_results.extend(generic_mock)

    logger.info("=" * 70)
    logger.info("OFFLINE PIPELINE COMPLETE:")
    logger.info(f"  PANKTI SHAH real call: {'SUCCESS' if real_call_success else 'FAILED (mocked)'}")
    logger.info(f"  Mocked vendors: {len(mock_results)}")
    logger.info(f"  Total offline results: {len(all_offline_results)}")
    logger.info("=" * 70)

    return all_offline_results


async def store_search_analytics(
    query: str,
    location: Optional[str],
    structured_query: StructuredQuery,
    results_count: int,
    search_time: float
):
    """Store search query in MongoDB analytics collection"""
    try:
        analytics_collection = db["analytics"]
        
        analytics_doc = {
            "query": query,
            "location": location,
            "parsed_query": structured_query.model_dump(),
            "results_count": results_count,
            "search_time": search_time,
            "timestamp": datetime.now(timezone.utc),
        }
        
        await analytics_collection.insert_one(analytics_doc)
        logger.debug(f"Stored analytics for query: {query}")
        
    except Exception as e:
        logger.error(f"Failed to store analytics: {e}")


@api_router.post("/webhooks/voice")
async def voice_webhook(payload: dict):
    """
    Webhook endpoint for Bland.ai call completion callbacks
    Stores call data in MongoDB
    """
    try:
        logger.info(f"Received voice webhook: {payload.get('call_id')}")
        
        voice_calls_collection = db["voice_calls"]
        
        webhook_doc = {
            "call_id": payload.get("call_id"),
            "status": payload.get("status"),
            "transcript": payload.get("concatenated_transcript"),
            "call_length": payload.get("call_length"),
            "metadata": payload.get("metadata", {}),
            "received_at": datetime.now(timezone.utc),
            "raw_payload": payload
        }
        
        await voice_calls_collection.insert_one(webhook_doc)
        logger.info(f"Stored webhook data for call: {payload.get('call_id')}")
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Error processing voice webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "PriceHunter API"
    }


@api_router.get("/stats")
async def get_stats():
    """
    Internal stats endpoint for analytics
    Returns usage metrics
    """
    try:
        analytics_collection = db["analytics"]
        
        # Total searches
        total_searches = await analytics_collection.count_documents({})
        
        # Searches today
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        searches_today = await analytics_collection.count_documents({
            "timestamp": {"$gte": today_start}
        })
        
        # Top queries (aggregation)
        top_queries_pipeline = [
            {"$group": {
                "_id": "$query",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        top_queries_cursor = analytics_collection.aggregate(top_queries_pipeline)
        top_queries = []
        async for doc in top_queries_cursor:
            top_queries.append({
                "query": doc["_id"],
                "count": doc["count"]
            })
        
        return {
            "total_searches": total_searches,
            "searches_today": searches_today,
            "top_queries": top_queries
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/test-voice-call")
async def test_voice_call():
    """
    Test endpoint to make a single real Bland.ai call
    Uses TEST_CALL_PHONE from environment
    """
    try:
        test_phone = os.environ.get('TEST_CALL_PHONE')
        bland_api_key = os.environ.get('BLAND_API_KEY')
        
        if not test_phone:
            raise HTTPException(status_code=400, detail="TEST_CALL_PHONE not configured")
        
        if not bland_api_key:
            raise HTTPException(status_code=400, detail="BLAND_API_KEY not configured")
        
        logger.info(f"Making test call to {test_phone}")
        
        # Import voice calling service
        from voice_calling import VoiceCallingService
        
        # Create service with real mode
        voice_service = VoiceCallingService(
            bland_api_key=bland_api_key,
            openai_api_key=os.environ.get('EMERGENT_LLM_KEY'),
            mock_mode=False  # Force real call
        )
        
        # Make test call
        result = await voice_service.call_vendor(
            vendor_name="Test Vendor",
            vendor_phone=test_phone,
            product="iPhone 15",
            category="electronics"
        )
        
        logger.info(f"Test call result: {result.status}")
        
        return {
            "status": "call_completed",
            "call_id": result.call_id,
            "call_status": result.status,
            "transcript": result.transcript,
            "extracted_data": {
                "price": result.price,
                "availability": result.availability,
                "negotiated": result.negotiated,
                "confidence": result.confidence
            },
            "notes": result.notes
        }
        
    except Exception as e:
        logger.error(f"Test call failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/")
async def root():
    return {"message": "PriceHunter API is running"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()