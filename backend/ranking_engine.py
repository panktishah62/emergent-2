"""
Comparator and Ranking Engine for PriceHunter
Scores and sorts results based on user intent
"""

import re
import logging
from typing import List, Dict, Literal
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ScoredResult(BaseModel):
    """Result with computed score"""
    result: Dict
    score: float
    score_breakdown: Dict[str, float]


# Scoring weights by intent
INTENT_WEIGHTS = {
    "cheapest": {
        "price": 0.60,
        "confidence": 0.20,
        "availability": 0.20,
    },
    "fastest": {
        "delivery_time": 0.50,
        "price": 0.20,
        "confidence": 0.15,
        "availability": 0.15,
    },
    "best_value": {
        "price": 0.35,
        "confidence": 0.25,
        "delivery_time": 0.20,
        "negotiated": 0.10,
        "availability": 0.10,
    },
    "nearest": {
        "source_offline": 0.30,
        "delivery_time": 0.30,
        "price": 0.20,
        "confidence": 0.20,
    }
}


def parse_delivery_time_to_minutes(delivery_str: str) -> int:
    """
    Parse delivery time string to minutes
    
    Examples:
    - "10 mins" → 10
    - "2 hours" → 120
    - "Same day" → 480 (8 hours)
    - "1-2 days" → 1440 (1 day)
    - "pickup now" → 0
    - "Express delivery (2 hours)" → 120
    """
    if not delivery_str:
        return 480  # Default to same day
    
    delivery_lower = delivery_str.lower()
    
    # Immediate pickup
    if any(word in delivery_lower for word in ["pickup now", "pick up now", "available now", "abhi"]):
        return 0
    
    # Minutes
    mins_match = re.search(r'(\d+)\s*min', delivery_lower)
    if mins_match:
        return int(mins_match.group(1))
    
    # Hours
    hours_match = re.search(r'(\d+)\s*hour', delivery_lower)
    if hours_match:
        return int(hours_match.group(1)) * 60
    
    # Take range start for "1-2 hours"
    range_hours_match = re.search(r'(\d+)-(\d+)\s*hour', delivery_lower)
    if range_hours_match:
        return int(range_hours_match.group(1)) * 60
    
    # Days
    days_match = re.search(r'(\d+)\s*day', delivery_lower)
    if days_match:
        return int(days_match.group(1)) * 24 * 60
    
    # Take range start for "1-2 days", "2-3 days"
    range_days_match = re.search(r'(\d+)-(\d+)\s*day', delivery_lower)
    if range_days_match:
        return int(range_days_match.group(1)) * 24 * 60
    
    # Common phrases
    time_mappings = {
        "same day": 480,      # 8 hours
        "next day": 1440,     # 24 hours
        "express": 120,       # 2 hours
        "slot": 480,          # Assume 8 hours for slots
        "local delivery": 120, # 2 hours for local
        "store pickup": 30,   # 30 mins to go to store
    }
    
    for phrase, minutes in time_mappings.items():
        if phrase in delivery_lower:
            return minutes
    
    # Default: assume same day
    return 480


def normalize_values(values: List[float]) -> List[float]:
    """
    Normalize list of values to 0-1 range
    Returns list of normalized values
    """
    if not values or len(values) == 0:
        return []
    
    min_val = min(values)
    max_val = max(values)
    
    # If all values are the same, return 0.5 for all
    if max_val == min_val:
        return [0.5] * len(values)
    
    # Normalize to 0-1
    normalized = [(v - min_val) / (max_val - min_val) for v in values]
    return normalized


def compute_availability_score(availability_str: str) -> float:
    """
    Convert availability string to score
    """
    if not availability_str:
        return 0.5
    
    availability_lower = availability_str.lower()
    
    if availability_lower in ["in stock", "available", "yes"]:
        return 1.0
    elif "limited" in availability_lower:
        return 0.7
    elif availability_lower in ["out of stock", "no", "unavailable"]:
        return 0.0
    else:
        return 0.5  # Unknown


def score_results(
    results: List[Dict],
    intent: Literal["cheapest", "fastest", "best_value", "nearest"]
) -> List[ScoredResult]:
    """
    Score all results based on intent
    
    Args:
        results: List of result dicts with price, delivery_time, confidence, etc.
        intent: User's search intent
    
    Returns:
        List of ScoredResult objects with scores and breakdowns
    """
    if not results:
        return []
    
    logger.info(f"Scoring {len(results)} results for intent: {intent}")
    
    weights = INTENT_WEIGHTS[intent]
    
    # Extract and normalize metrics
    prices = []
    delivery_times = []
    confidences = []
    availabilities = []
    source_types = []
    negotiated_flags = []
    
    for result in results:
        # Price (handle None)
        price = result.get("price")
        prices.append(price if price is not None else float('inf'))
        
        # Delivery time in minutes
        delivery_str = result.get("delivery_time", "")
        delivery_mins = parse_delivery_time_to_minutes(delivery_str)
        delivery_times.append(delivery_mins)
        
        # Confidence
        confidence = result.get("confidence", 0.5)
        confidences.append(confidence)
        
        # Availability
        availability_str = result.get("availability", "")
        availability_score = compute_availability_score(availability_str)
        availabilities.append(availability_score)
        
        # Source type (for "nearest" intent)
        source_type = result.get("source_type", "ONLINE")
        source_types.append(1.0 if source_type == "OFFLINE" else 0.0)
        
        # Negotiated flag (for "best_value" intent)
        negotiated = result.get("negotiated", False)
        negotiated_flags.append(negotiated)
    
    # Normalize price (lower is better, so invert)
    valid_prices = [p for p in prices if p != float('inf')]
    if valid_prices:
        normalized_prices = normalize_values(prices)
        # Invert: lower price = higher score
        price_scores = [1 - p if prices[i] != float('inf') else 0.0 
                       for i, p in enumerate(normalized_prices)]
    else:
        price_scores = [0.0] * len(prices)
    
    # Normalize delivery time (lower is better, so invert)
    normalized_delivery = normalize_values(delivery_times)
    delivery_scores = [1 - d for d in normalized_delivery]
    
    # Confidence is already 0-1, but normalize to balance outliers
    confidence_scores = normalize_values(confidences)
    
    # Availability is already scored 0-1
    availability_scores = availabilities
    
    # Source type is already 0 or 1
    source_scores = source_types
    
    # Negotiated is boolean
    negotiated_scores = [1.0 if n else 0.0 for n in negotiated_flags]
    
    # Compute final scores
    scored_results = []
    
    for i, result in enumerate(results):
        breakdown = {}
        total_score = 0.0
        
        # Apply weights based on intent
        if "price" in weights:
            price_component = price_scores[i] * weights["price"]
            breakdown["price"] = price_component
            total_score += price_component
        
        if "delivery_time" in weights:
            delivery_component = delivery_scores[i] * weights["delivery_time"]
            breakdown["delivery_time"] = delivery_component
            total_score += delivery_component
        
        if "confidence" in weights:
            confidence_component = confidence_scores[i] * weights["confidence"]
            breakdown["confidence"] = confidence_component
            total_score += confidence_component
        
        if "availability" in weights:
            availability_component = availability_scores[i] * weights["availability"]
            breakdown["availability"] = availability_component
            total_score += availability_component
        
        if "source_offline" in weights:
            source_component = source_scores[i] * weights["source_offline"]
            breakdown["source_offline"] = source_component
            total_score += source_component
        
        if "negotiated" in weights:
            negotiated_component = negotiated_scores[i] * weights["negotiated"]
            breakdown["negotiated"] = negotiated_component
            total_score += negotiated_component
        
        # Apply 5% bonus if negotiated
        if negotiated_flags[i]:
            bonus_multiplier = 1.05
            total_score *= bonus_multiplier
            breakdown["negotiated_bonus"] = 0.05
        
        scored_results.append(ScoredResult(
            result=result,
            score=round(total_score, 4),
            score_breakdown=breakdown
        ))
    
    logger.info(f"Scoring complete. Top score: {max(r.score for r in scored_results):.4f}")
    
    return scored_results


def rank_results(
    results: List[Dict],
    intent: Literal["cheapest", "fastest", "best_value", "nearest"]
) -> List[Dict]:
    """
    Score and rank results based on intent
    Returns sorted list of results (highest score first)
    
    Args:
        results: List of search results
        intent: User's search intent
    
    Returns:
        Sorted list of results with rank added
    """
    # Score all results
    scored_results = score_results(results, intent)
    
    # Sort by score (descending)
    scored_results.sort(key=lambda x: x.score, reverse=True)
    
    # Add rank to results and extract
    ranked_results = []
    for rank, scored in enumerate(scored_results, 1):
        result = scored.result.copy()
        result["rank"] = rank
        result["score"] = scored.score
        result["score_breakdown"] = scored.score_breakdown
        ranked_results.append(result)
    
    logger.info(
        f"Ranked {len(ranked_results)} results. "
        f"Top: {ranked_results[0]['vendor_name']} (score: {ranked_results[0]['score']:.4f})"
    )
    
    return ranked_results


def debug_scoring(results: List[Dict], intent: str):
    """
    Print detailed scoring breakdown for debugging
    """
    scored = score_results(results, intent)
    scored.sort(key=lambda x: x.score, reverse=True)
    
    print(f"\n{'='*80}")
    print(f"SCORING DEBUG - Intent: {intent}")
    print(f"{'='*80}\n")
    
    for i, sr in enumerate(scored[:5], 1):  # Top 5
        result = sr.result
        print(f"{i}. {result['vendor_name']} - Score: {sr.score:.4f}")
        print(f"   Price: ₹{result.get('price', 'N/A')}")
        print(f"   Delivery: {result.get('delivery_time', 'N/A')}")
        print(f"   Source: {result.get('source_type', 'N/A')}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        print(f"   Breakdown: {sr.score_breakdown}")
        print()
