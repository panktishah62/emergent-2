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
    parsed_intent: dict

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

async def parse_query_with_openai(query: str, location: Optional[str]) -> dict:
    """Parse user query using OpenAI to extract product, category, location, and intent"""
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        
        system_message = """You are a query parser for a price comparison engine in India. 
        Extract the following information from the user's query:
        - product: the main product name
        - category: the product category (electronics, groceries, fashion, etc.)
        - intent: one of [cheapest, fastest, nearest, best_value]
        - location: the location mentioned (or use the provided location parameter)
        
        Return ONLY a valid JSON object with these exact keys. No additional text.
        Example: {"product": "iPhone 15", "category": "electronics", "intent": "cheapest", "location": "Koramangala"}
        """
        
        chat = LlmChat(
            api_key=api_key,
            session_id=str(uuid.uuid4()),
            system_message=system_message
        ).with_model("openai", "gpt-4o-mini")
        
        user_message = UserMessage(
            text=f"Query: {query}\nProvided Location: {location or 'Not provided'}"
        )
        
        response = await chat.send_message(user_message)
        
        # Parse the JSON response
        import json
        parsed = json.loads(response)
        
        logger.info(f"Parsed query: {parsed}")
        return parsed
        
    except Exception as e:
        logger.error(f"Error parsing query with OpenAI: {e}")
        # Fallback to basic parsing
        return {
            "product": query.split()[0] if query else "product",
            "category": "general",
            "intent": "cheapest",
            "location": location or "India"
        }

@api_router.post("/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """Main search endpoint that processes queries and returns ranked results"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Step 1: Parse query with OpenAI
        parsed_intent = await parse_query_with_openai(request.query, request.location)
        
        # Step 2: Generate mock online results
        online_results = generate_mock_online_results(
            parsed_intent.get("product", "product"),
            parsed_intent.get("category", "general"),
            count=random.randint(4, 7)
        )
        
        # Step 3: Generate mock offline results
        offline_results = generate_mock_offline_results(
            parsed_intent.get("product", "product"),
            parsed_intent.get("category", "general"),
            parsed_intent.get("location", request.location or "India"),
            count=random.randint(2, 4)
        )
        
        # Step 4: Combine and rank results
        all_results = online_results + offline_results
        
        # Sort by price (cheapest first) or by confidence for "best_value"
        intent = parsed_intent.get("intent", "cheapest")
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
            parsed_intent=parsed_intent
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