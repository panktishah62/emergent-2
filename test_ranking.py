#!/usr/bin/env python3
"""Test the ranking engine with detailed scoring breakdown"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from ranking_engine import rank_results, debug_scoring

# Sample results for testing
test_results = [
    {
        "source_type": "ONLINE",
        "vendor_name": "Blinkit",
        "price": 100.0,
        "delivery_time": "10 mins",
        "confidence": 0.92,
        "product_name": "Milk",
        "category": "groceries",
        "availability": "In Stock",
        "negotiated": False
    },
    {
        "source_type": "OFFLINE",
        "vendor_name": "Local Dairy Store",
        "price": 80.0,
        "delivery_time": "Pick up now",
        "confidence": 0.85,
        "product_name": "Milk",
        "category": "groceries",
        "availability": "In Stock",
        "negotiated": True
    },
    {
        "source_type": "ONLINE",
        "vendor_name": "BigBasket",
        "price": 95.0,
        "delivery_time": "Same day delivery",
        "confidence": 0.88,
        "product_name": "Milk",
        "category": "groceries",
        "availability": "In Stock",
        "negotiated": False
    },
    {
        "source_type": "OFFLINE",
        "vendor_name": "Corner Shop",
        "price": 110.0,
        "delivery_time": "Local delivery (2 hours)",
        "confidence": 0.78,
        "product_name": "Milk",
        "category": "groceries",
        "availability": "Limited Stock",
        "negotiated": False
    },
]

print("\n" + "="*80)
print("RANKING ENGINE TEST - Comparing Different Intents")
print("="*80 + "\n")

# Test each intent
for intent in ["cheapest", "fastest", "best_value", "nearest"]:
    print(f"\n{'='*80}")
    print(f"Intent: {intent.upper()}")
    print(f"{'='*80}")
    
    ranked = rank_results(test_results, intent)
    
    print(f"\nRanked Results:")
    for r in ranked:
        print(f"  {r['rank']}. {r['vendor_name']:20} | "
              f"₹{r['price']:6.2f} | {r['delivery_time']:25} | "
              f"Score: {r['score']:.4f}")
    
    print(f"\nScore Breakdown (Top result):")
    top = ranked[0]
    for component, value in top['score_breakdown'].items():
        print(f"  {component:20}: {value:.4f}")

print(f"\n{'='*80}\n")
