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

# Mock data generators
ONLINE_PLATFORMS = [
    "Amazon India", "Flipkart", "Blinkit", "Zepto", 
    "Croma", "BigBasket", "Myntra", "Reliance Digital",
    "Vijay Sales", "JioMart"
]

OFFLINE_VENDORS = [
    "Sharma Electronics", "Kumar Store", "Patel Traders",
    "Singh Mart", "Gupta Super Market", "Reddy Shopping Center",
    "Mehta Electronics", "Desai General Store", "Joshi Bazaar",
    "Rao Provisions"
]

def generate_mock_online_results(product: str, category: str, count: int = 5) -> List[dict]:
    """Generate mock online platform results"""
    results = []
    base_price = random.randint(1000, 50000) if category.lower() in ["electronics", "phone", "laptop"] else random.randint(50, 5000)
    
    for i in range(count):
        vendor = random.choice(ONLINE_PLATFORMS)
        price_variation = random.uniform(0.85, 1.15)
        price = round(base_price * price_variation, 2)
        
        delivery_options = [
            "Same day delivery",
            "Next day delivery",
            "2-3 days",
            "3-5 days",
            "Express delivery (2 hours)"
        ]
        
        results.append({
            "source_type": "ONLINE",
            "vendor_name": vendor,
            "price": price,
            "delivery_time": random.choice(delivery_options),
            "confidence": random.uniform(0.75, 0.98),
            "product_name": product,
            "category": category,
            "availability": "In Stock"
        })
    
    return results

def generate_mock_offline_results(product: str, category: str, location: str, count: int = 3) -> List[dict]:
    """Generate mock offline vendor results (simulating Bland.ai calls)"""
    results = []
    base_price = random.randint(1000, 50000) if category.lower() in ["electronics", "phone", "laptop"] else random.randint(50, 5000)
    
    for i in range(count):
        vendor = random.choice(OFFLINE_VENDORS)
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
        
        # Step 2: Generate mock online results
        online_results = generate_mock_online_results(
            structured_query.product,
            structured_query.category,
            count=random.randint(4, 7)
        )
        
        # Step 3: Generate mock offline results
        offline_results = generate_mock_offline_results(
            structured_query.product,
            structured_query.category,
            structured_query.location,
            count=random.randint(2, 4)
        )
        
        # Step 4: Combine and rank results based on intent
        all_results = online_results + offline_results
        
        intent = structured_query.intent
        if intent == "cheapest":
            all_results.sort(key=lambda x: x["price"])
        elif intent == "fastest":
            # Sort by delivery time (prioritize same day, express)
            delivery_priority = {
                "Express delivery (2 hours)": 1,
                "Pick up now": 1,
                "Local delivery (1-2 hours)": 2,
                "Pick up in 30 mins": 1,
                "Same day delivery": 3,
                "Next day delivery": 4,
                "2-3 days": 5,
                "3-5 days": 6
            }
            all_results.sort(key=lambda x: delivery_priority.get(x["delivery_time"], 10))
        elif intent == "best_value":
            # Sort by a combination of price and confidence
            all_results.sort(key=lambda x: x["price"] / x["confidence"])
        else:  # nearest
            # Prioritize offline vendors
            all_results.sort(key=lambda x: (0 if x["source_type"] == "OFFLINE" else 1, x["price"]))
        
        # Step 5: Create SearchResult objects with ranks
        search_results = []
        for idx, result in enumerate(all_results):
            search_results.append(SearchResult(
                id=str(uuid.uuid4()),
                rank=idx + 1,
                is_best_deal=(idx == 0),
                **result
            ))
        
        end_time = asyncio.get_event_loop().time()
        search_time = round(end_time - start_time, 2)
        
        # Step 6: Return response
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