from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone
import asyncio
import random
from emergentintegrations.llm.chat import LlmChat, UserMessage
import googlemaps
import phonenumbers
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
    
    try:
        # Step 1: Parse query with OpenAI (with retry and fallback)
        structured_query = await parse_query_with_openai(request.query, request.location)
        
        # Step 2: Run online pipeline concurrently
        logger.info(f"Running online pipeline for {structured_query.category}: {structured_query.product}")
        online_unified_results = await run_online_pipeline(
            structured_query.product,
            structured_query.category,
            structured_query.location
        )
        
        # Convert unified results to search result format
        online_results = [
            unified_to_search_result(r, structured_query.product, structured_query.category)
            for r in online_unified_results
        ]
        
        logger.info(f"Online pipeline returned {len(online_results)} results")
        
        # Step 3: Discover local vendors using Google Places API
        discovered_vendors = await discover_local_vendors_with_google_places(
            structured_query.product,
            structured_query.category,
            structured_query.location
        )
        
        # Step 4: Call vendors using AI voice calling (Bland.ai)
        offline_results = []
        
        if discovered_vendors:
            # Make AI voice calls to discovered vendors
            offline_results = await call_vendors_with_ai(
                discovered_vendors,
                structured_query.product,
                structured_query.category
            )
        
        # Fallback to mock data if no successful calls
        if len(offline_results) < 2:
            logger.info("Adding mock offline vendors to supplement voice call results")
            mock_offline = generate_mock_offline_results(
                structured_query.product,
                structured_query.category,
                structured_query.location,
                count=max(2, 3 - len(offline_results))
            )
            offline_results.extend(mock_offline)
        
        # Step 5: Rank results using intelligent scoring engine
        all_results = online_results + offline_results
        
        logger.info(f"Ranking {len(all_results)} results by intent: {structured_query.intent}")
        
        # Use ranking engine to score and sort results
        ranked_results = rank_results(all_results, structured_query.intent)
        
        logger.info(
            f"Top result: {ranked_results[0]['vendor_name']} "
            f"(score: {ranked_results[0].get('score', 0):.4f})"
        )
        
        # Step 6: Create SearchResult objects with ranks from ranking engine
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
        
        # Step 7: Return response
        return SearchResponse(
            results=search_results,
            total_results=len(search_results),
            online_count=len(online_results),
            offline_count=len(offline_results),
            search_time=search_time,
            parsed_query=structured_query
        )
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
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