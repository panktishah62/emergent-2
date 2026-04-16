#!/usr/bin/env python3
"""Test script for query parsing logic with retry and fallback"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from server import parse_query_with_openai

async def test_query_parsing():
    """Test various query parsing scenarios"""
    
    test_cases = [
        {
            "query": "cheap tomatoes in Rajkot",
            "location": None,
            "expected": {
                "product": "tomatoes",
                "category": "groceries",
                "location": "Rajkot",
                "intent": "cheapest"
            }
        },
        {
            "query": "fastest delivery iPhone 15 Bangalore",
            "location": None,
            "expected": {
                "product": "iPhone 15",
                "category": "electronics",
                "location": "Bangalore",
                "intent": "fastest"
            }
        },
        {
            "query": "best value laptop",
            "location": "Mumbai",
            "expected": {
                "product": "laptop",
                "category": "electronics",
                "location": "Mumbai",
                "intent": "best_value"
            }
        },
        {
            "query": "nearest pharmacy for paracetamol",
            "location": "Delhi",
            "expected": {
                "product": "paracetamol",
                "category": "medicine",
                "location": "Delhi",
                "intent": "nearest"
            }
        }
    ]
    
    print("=" * 80)
    print("QUERY PARSING TEST SUITE")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] Query: '{test['query']}'")
        print(f"Location Parameter: {test['location']}")
        
        try:
            result = await parse_query_with_openai(test['query'], test['location'])
            
            print(f"\n✓ Parsed Result:")
            print(f"  Product: {result.product}")
            print(f"  Category: {result.category}")
            print(f"  Location: {result.location}")
            print(f"  Intent: {result.intent}")
            print(f"  Raw Query: {result.raw_query}")
            
            # Validate
            expected = test['expected']
            checks = []
            
            if result.product.lower() in expected['product'].lower() or expected['product'].lower() in result.product.lower():
                checks.append(("Product", True))
            else:
                checks.append(("Product", False))
            
            if result.category == expected['category']:
                checks.append(("Category", True))
            else:
                checks.append(("Category", False))
            
            if result.location == expected['location']:
                checks.append(("Location", True))
            else:
                checks.append(("Location", False))
            
            if result.intent == expected['intent']:
                checks.append(("Intent", True))
            else:
                checks.append(("Intent", False))
            
            all_passed = all(check[1] for check in checks)
            
            print(f"\n  Validation:")
            for field, status in checks:
                print(f"    {field}: {'✓ PASS' if status else '✗ FAIL'}")
            
            if all_passed:
                print(f"\n  ✓ Test {i} PASSED")
                passed += 1
            else:
                print(f"\n  ✗ Test {i} FAILED")
                failed += 1
                
        except Exception as e:
            print(f"\n  ✗ Error: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return passed == len(test_cases)

if __name__ == "__main__":
    success = asyncio.run(test_query_parsing())
    sys.exit(0 if success else 1)
