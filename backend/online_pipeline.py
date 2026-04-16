"""
Online Pipeline for PriceHunter
Simulates searches across Indian e-commerce platforms with realistic data
"""

import asyncio
import random
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class UnifiedResult(BaseModel):
    """Unified result schema for both online and offline vendors"""
    source_type: Literal["online", "offline"]
    name: str  # Platform or vendor name
    price: float
    currency: str = "INR"
    delivery_time: str
    availability: bool
    negotiated: bool = False
    confidence: float
    url: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: str


class PlatformConfig(BaseModel):
    """Configuration for an e-commerce platform"""
    name: str
    delivery_times: List[str]
    url_template: str
    confidence_range: tuple[float, float] = (0.75, 0.95)


# Platform configurations by category
PLATFORM_MAPPING = {
    "electronics": [
        PlatformConfig(
            name="Amazon India",
            delivery_times=["1-2 days", "Next day delivery", "Same day delivery"],
            url_template="https://amazon.in/s?k={product}",
            confidence_range=(0.85, 0.95)
        ),
        PlatformConfig(
            name="Flipkart",
            delivery_times=["2-3 days", "Next day delivery", "Same day delivery"],
            url_template="https://flipkart.com/search?q={product}",
            confidence_range=(0.82, 0.94)
        ),
        PlatformConfig(
            name="Croma",
            delivery_times=["3-5 days", "Store pickup available"],
            url_template="https://croma.com/search?q={product}",
            confidence_range=(0.78, 0.90)
        ),
        PlatformConfig(
            name="Reliance Digital",
            delivery_times=["3-5 days", "Store pickup today"],
            url_template="https://reliancedigital.in/search?q={product}",
            confidence_range=(0.75, 0.88)
        ),
        PlatformConfig(
            name="Vijay Sales",
            delivery_times=["4-6 days", "Store pickup available"],
            url_template="https://vijaysales.com/search/{product}",
            confidence_range=(0.72, 0.87)
        ),
    ],
    
    "groceries": [
        PlatformConfig(
            name="Blinkit",
            delivery_times=["10 mins", "15 mins", "20 mins"],
            url_template="https://blinkit.com/search?q={product}",
            confidence_range=(0.88, 0.95)
        ),
        PlatformConfig(
            name="Zepto",
            delivery_times=["10 mins", "12 mins", "15 mins"],
            url_template="https://zepto.com/search?q={product}",
            confidence_range=(0.87, 0.94)
        ),
        PlatformConfig(
            name="Swiggy Instamart",
            delivery_times=["15-20 mins", "25-30 mins"],
            url_template="https://swiggy.com/instamart/search?q={product}",
            confidence_range=(0.85, 0.93)
        ),
        PlatformConfig(
            name="BigBasket",
            delivery_times=["Next day delivery", "Same day delivery", "Slot: 6-9 PM"],
            url_template="https://bigbasket.com/ps/?q={product}",
            confidence_range=(0.83, 0.92)
        ),
        PlatformConfig(
            name="JioMart",
            delivery_times=["1-2 days", "Next day delivery"],
            url_template="https://jiomart.com/search/{product}",
            confidence_range=(0.80, 0.90)
        ),
    ],
    
    "medicine": [
        PlatformConfig(
            name="PharmEasy",
            delivery_times=["24 hours", "Same day delivery", "2-3 hours"],
            url_template="https://pharmeasy.in/search/all?name={product}",
            confidence_range=(0.85, 0.93)
        ),
        PlatformConfig(
            name="1mg",
            delivery_times=["24 hours", "Same day delivery"],
            url_template="https://1mg.com/search/all?name={product}",
            confidence_range=(0.84, 0.92)
        ),
        PlatformConfig(
            name="Apollo Pharmacy",
            delivery_times=["2-3 days", "Same day delivery", "Store pickup"],
            url_template="https://apollopharmacy.in/search-medicines/{product}",
            confidence_range=(0.82, 0.91)
        ),
        PlatformConfig(
            name="Netmeds",
            delivery_times=["2-3 days", "Express delivery (24h)"],
            url_template="https://netmeds.com/catalogsearch/result/{product}",
            confidence_range=(0.80, 0.90)
        ),
    ],
    
    "clothing": [
        PlatformConfig(
            name="Myntra",
            delivery_times=["3-4 days", "2-3 days"],
            url_template="https://myntra.com/{product}",
            confidence_range=(0.85, 0.93)
        ),
        PlatformConfig(
            name="Ajio",
            delivery_times=["4-5 days", "3-4 days"],
            url_template="https://ajio.com/search/?text={product}",
            confidence_range=(0.82, 0.91)
        ),
        PlatformConfig(
            name="Amazon India",
            delivery_times=["2-3 days", "Next day delivery"],
            url_template="https://amazon.in/s?k={product}",
            confidence_range=(0.84, 0.93)
        ),
        PlatformConfig(
            name="Flipkart",
            delivery_times=["3-4 days", "2-3 days"],
            url_template="https://flipkart.com/search?q={product}",
            confidence_range=(0.83, 0.92)
        ),
        PlatformConfig(
            name="Meesho",
            delivery_times=["5-7 days", "4-6 days"],
            url_template="https://meesho.com/search?q={product}",
            confidence_range=(0.75, 0.88)
        ),
    ],
    
    "hardware": [
        PlatformConfig(
            name="Amazon India",
            delivery_times=["1-2 days", "2-3 days"],
            url_template="https://amazon.in/s?k={product}",
            confidence_range=(0.83, 0.92)
        ),
        PlatformConfig(
            name="Flipkart",
            delivery_times=["2-3 days", "3-4 days"],
            url_template="https://flipkart.com/search?q={product}",
            confidence_range=(0.81, 0.91)
        ),
        PlatformConfig(
            name="IndiaMART",
            delivery_times=["3-7 days", "Varies by seller"],
            url_template="https://indiamart.com/search.mp?ss={product}",
            confidence_range=(0.75, 0.87)
        ),
        PlatformConfig(
            name="Moglix",
            delivery_times=["3-5 days", "5-7 days"],
            url_template="https://moglix.com/search?q={product}",
            confidence_range=(0.73, 0.86)
        ),
    ],
    
    "general": [
        PlatformConfig(
            name="Amazon India",
            delivery_times=["1-2 days", "2-3 days", "Next day delivery"],
            url_template="https://amazon.in/s?k={product}",
            confidence_range=(0.84, 0.93)
        ),
        PlatformConfig(
            name="Flipkart",
            delivery_times=["2-3 days", "3-4 days", "Next day delivery"],
            url_template="https://flipkart.com/search?q={product}",
            confidence_range=(0.82, 0.92)
        ),
        PlatformConfig(
            name="Snapdeal",
            delivery_times=["3-5 days", "4-6 days"],
            url_template="https://snapdeal.com/search?keyword={product}",
            confidence_range=(0.75, 0.87)
        ),
    ],
}


# Base price ranges by category (in INR)
CATEGORY_PRICE_RANGES = {
    "electronics": (5000, 150000),
    "groceries": (20, 500),
    "medicine": (50, 2000),
    "clothing": (300, 5000),
    "hardware": (100, 10000),
    "general": (100, 5000),
}


def get_base_price(category: str, product: str) -> float:
    """
    Determine a base price for a product based on category and product keywords
    """
    min_price, max_price = CATEGORY_PRICE_RANGES.get(category, (100, 5000))
    
    # Adjust base price based on product keywords
    product_lower = product.lower()
    
    # High-end electronics keywords
    if any(keyword in product_lower for keyword in ["iphone", "macbook", "laptop", "gaming", "premium", "pro"]):
        base = random.uniform(max_price * 0.6, max_price)
    # Mid-range keywords
    elif any(keyword in product_lower for keyword in ["phone", "tablet", "watch", "speaker"]):
        base = random.uniform(min_price * 2, max_price * 0.5)
    # Budget keywords
    elif any(keyword in product_lower for keyword in ["basic", "budget", "simple"]):
        base = random.uniform(min_price, min_price * 1.5)
    else:
        # Default: mid-range
        base = random.uniform(min_price * 1.5, max_price * 0.4)
    
    return round(base, 2)


async def search_platform(
    platform: PlatformConfig,
    product: str,
    base_price: float,
    category: str
) -> UnifiedResult:
    """
    Simulate searching a single platform for a product
    Returns a UnifiedResult with mock data
    """
    # Simulate API latency (0.2 to 1 second)
    latency = random.uniform(0.2, 1.0)
    await asyncio.sleep(latency)
    
    # 90% availability chance
    available = random.random() < 0.90
    
    # Price variation ±15%
    price_variation = random.uniform(0.85, 1.15)
    price = round(base_price * price_variation, 2)
    
    # Random delivery time from platform's options
    delivery_time = random.choice(platform.delivery_times)
    
    # Confidence score within platform's range
    confidence = round(random.uniform(*platform.confidence_range), 2)
    
    # Generate URL with product
    url = platform.url_template.format(product=product.replace(" ", "+"))
    
    logger.debug(
        f"Searched {platform.name}: ₹{price}, {delivery_time}, "
        f"Available: {available}, Confidence: {confidence}"
    )
    
    return UnifiedResult(
        source_type="online",
        name=platform.name,
        price=price,
        currency="INR",
        delivery_time=delivery_time,
        availability=available,
        negotiated=False,
        confidence=confidence,
        url=url,
        phone=None,
        address=None,
        notes=f"TODO: Replace with real {platform.name} API integration"
    )


async def run_online_pipeline(
    product: str,
    category: str,
    location: Optional[str] = None
) -> List[UnifiedResult]:
    """
    Run the complete online pipeline:
    1. Map category to relevant platforms
    2. Determine base price
    3. Search all platforms concurrently
    4. Return unified results
    """
    logger.info(f"Running online pipeline: product='{product}', category='{category}'")
    
    # Get platforms for this category
    platforms = PLATFORM_MAPPING.get(category, PLATFORM_MAPPING["general"])
    logger.info(f"Searching {len(platforms)} platforms for category '{category}'")
    
    # Determine base price
    base_price = get_base_price(category, product)
    logger.info(f"Base price for '{product}': ₹{base_price:.2f}")
    
    # Create concurrent search tasks for all platforms
    search_tasks = [
        search_platform(platform, product, base_price, category)
        for platform in platforms
    ]
    
    # Run all searches concurrently
    start_time = asyncio.get_event_loop().time()
    results = await asyncio.gather(*search_tasks)
    end_time = asyncio.get_event_loop().time()
    
    # Filter out unavailable results
    available_results = [r for r in results if r.availability]
    
    logger.info(
        f"Online pipeline completed in {end_time - start_time:.2f}s: "
        f"{len(available_results)}/{len(results)} results available"
    )
    
    return available_results


# Backward compatibility function for existing code
def generate_mock_online_results(product: str, category: str, count: int = 5) -> List[dict]:
    """
    Legacy function for backward compatibility
    Converts UnifiedResult to old dict format
    """
    # Run the new pipeline synchronously
    results = asyncio.run(run_online_pipeline(product, category))
    
    # Convert to old format and limit to requested count
    legacy_results = []
    for result in results[:count]:
        legacy_results.append({
            "source_type": "ONLINE",
            "vendor_name": result.name,
            "price": result.price,
            "delivery_time": result.delivery_time,
            "confidence": result.confidence,
            "product_name": product,
            "category": category,
            "availability": "In Stock" if result.availability else "Out of Stock"
        })
    
    return legacy_results
