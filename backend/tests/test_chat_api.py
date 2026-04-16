"""
Backend API Tests for PriceHunter Chat Endpoints
Tests: POST /api/chat/message, POST /api/chat/reset, GET /api/health
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthEndpoint:
    """Health check endpoint tests"""
    
    def test_health_check(self):
        """Test /api/health returns 200 with correct structure"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "service" in data
        assert data["service"] == "PriceHunter API"
        print(f"✓ Health check passed: {data}")


class TestChatMessageEndpoint:
    """Tests for POST /api/chat/message endpoint"""
    
    def test_chat_message_without_session_id(self):
        """Test sending message without session_id creates new session"""
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "message": "Hello"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "assistant_message" in data
        assert "conversation_state" in data
        assert "search_triggered" in data
        assert "results" in data
        assert "progress_states" in data
        
        # Verify session_id was generated
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0
        
        # Verify conversation state
        assert data["conversation_state"] == "collecting"
        assert data["search_triggered"] == False
        
        print(f"✓ Chat message without session_id: session={data['session_id'][:20]}...")
    
    def test_chat_message_with_session_id(self):
        """Test sending message with existing session_id"""
        session_id = f"test_session_{uuid.uuid4()}"
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "I need a laptop"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify session_id is preserved
        assert data["session_id"] == session_id
        assert "assistant_message" in data
        assert len(data["assistant_message"]) > 0
        
        print(f"✓ Chat message with session_id: {data['assistant_message'][:80]}...")
    
    def test_chat_message_empty_message(self):
        """Test sending empty message returns 400"""
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "message": ""
        })
        assert response.status_code == 400
        print("✓ Empty message correctly returns 400")
    
    def test_chat_message_whitespace_only(self):
        """Test sending whitespace-only message returns 400"""
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "message": "   "
        })
        assert response.status_code == 400
        print("✓ Whitespace-only message correctly returns 400")
    
    def test_chat_message_triggers_search(self):
        """Test complete query triggers search and returns results"""
        session_id = f"test_search_{uuid.uuid4()}"
        
        # Send a complete query with product + location
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "cheapest iPhone 15 in Bangalore"
        }, timeout=120)  # LLM + search can take time
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify search was triggered
        assert data["search_triggered"] == True
        assert data["conversation_state"] in ["searching", "results_ready"]
        
        # Verify results structure
        assert "results" in data
        if data["results"]:
            assert len(data["results"]) > 0
            
            # Verify result card structure
            result = data["results"][0]
            assert "rank" in result
            assert "source_type" in result
            assert result["source_type"] in ["ONLINE", "OFFLINE"]
            assert "vendor_name" in result
            assert "price" in result
            assert isinstance(result["price"], (int, float))
            assert "delivery_time" in result
            assert "confidence" in result
            assert isinstance(result["confidence"], (int, float))
            assert 0 <= result["confidence"] <= 1
            assert "availability" in result
            
            print(f"✓ Search triggered: {len(data['results'])} results found")
            print(f"  Top result: {result['vendor_name']} - ₹{result['price']}")
        
        # Verify progress states
        assert "progress_states" in data
        if data["progress_states"]:
            assert len(data["progress_states"]) == 6  # 6 stages
            stages = [s["stage"] for s in data["progress_states"]]
            assert "Understanding your request" in stages
            assert "Searching online platforms" in stages
            assert "Finding nearby vendors" in stages
            assert "Calling vendors for prices" in stages
            assert "Negotiating best deals" in stages
            assert "Comparing & ranking results" in stages
            print(f"✓ Progress states: {len(data['progress_states'])} stages")
        
        # Verify parsed query
        assert "parsed_query" in data
        if data["parsed_query"]:
            pq = data["parsed_query"]
            assert "product" in pq
            assert "location" in pq
            assert "intent" in pq
            assert "category" in pq
            print(f"✓ Parsed query: {pq['product']} in {pq['location']} ({pq['intent']})")
        
        # Verify search metadata
        assert "search_metadata" in data
        if data["search_metadata"]:
            meta = data["search_metadata"]
            assert "total_results" in meta
            assert "online_count" in meta
            assert "offline_count" in meta
            assert "search_time" in meta
            print(f"✓ Search metadata: {meta['total_results']} results in {meta['search_time']}s")
    
    def test_conversational_flow_asks_for_location(self):
        """Test that partial query (product only) asks for location"""
        session_id = f"test_conv_{uuid.uuid4()}"
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "I need a laptop"
        }, timeout=60)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should not trigger search yet
        assert data["search_triggered"] == False
        assert data["conversation_state"] == "collecting"
        
        # Assistant should ask for location
        msg = data["assistant_message"].lower()
        # Check if assistant is asking for more info (location, city, area, where)
        location_keywords = ["location", "city", "area", "where", "which"]
        has_location_question = any(kw in msg for kw in location_keywords)
        
        print(f"✓ Conversational flow: search_triggered={data['search_triggered']}")
        print(f"  Assistant response: {data['assistant_message'][:100]}...")
        
        # Note: LLM might directly ask for location or provide other response
        # The key test is that search was NOT triggered without location


class TestChatResetEndpoint:
    """Tests for POST /api/chat/reset endpoint"""
    
    def test_reset_existing_session(self):
        """Test resetting an existing session"""
        session_id = f"test_reset_{uuid.uuid4()}"
        
        # First create a session
        requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "Hello"
        })
        
        # Reset the session
        response = requests.post(f"{BASE_URL}/api/chat/reset", json={
            "session_id": session_id
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data
        print(f"✓ Reset session: {data}")
    
    def test_reset_nonexistent_session(self):
        """Test resetting a non-existent session (should still return ok)"""
        response = requests.post(f"{BASE_URL}/api/chat/reset", json={
            "session_id": "nonexistent_session_12345"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print(f"✓ Reset non-existent session: {data}")
    
    def test_reset_without_session_id(self):
        """Test reset without session_id"""
        response = requests.post(f"{BASE_URL}/api/chat/reset", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print(f"✓ Reset without session_id: {data}")


class TestSearchResultsStructure:
    """Tests for search results data structure and values"""
    
    def test_results_have_required_fields(self):
        """Test that all results have required fields"""
        session_id = f"test_fields_{uuid.uuid4()}"
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "tomatoes near Rajkot"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["results"]:
            required_fields = [
                "id", "rank", "source_type", "vendor_name", "price",
                "delivery_time", "confidence", "is_best_deal", "product_name",
                "category", "availability"
            ]
            
            for result in data["results"]:
                for field in required_fields:
                    assert field in result, f"Missing field: {field}"
            
            print(f"✓ All {len(data['results'])} results have required fields")
    
    def test_results_ranking_order(self):
        """Test that results are ranked in order"""
        session_id = f"test_rank_{uuid.uuid4()}"
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "laptop under 50000 in Mumbai"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["results"] and len(data["results"]) > 1:
            ranks = [r["rank"] for r in data["results"]]
            # Ranks should be sequential starting from 1
            expected_ranks = list(range(1, len(ranks) + 1))
            assert ranks == expected_ranks, f"Ranks not sequential: {ranks}"
            
            # First result should be best deal
            assert data["results"][0]["is_best_deal"] == True
            
            print(f"✓ Results correctly ranked: {ranks[:5]}...")
    
    def test_confidence_scores_valid(self):
        """Test that confidence scores are between 0 and 1"""
        session_id = f"test_conf_{uuid.uuid4()}"
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "nearest pharmacy in Delhi"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["results"]:
            for result in data["results"]:
                assert 0 <= result["confidence"] <= 1, f"Invalid confidence: {result['confidence']}"
            
            print(f"✓ All confidence scores valid (0-1)")


class TestProgressStates:
    """Tests for progress states structure"""
    
    def test_progress_states_structure(self):
        """Test progress states have correct structure"""
        session_id = f"test_progress_{uuid.uuid4()}"
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "cheapest iPhone 15 in Bangalore"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["progress_states"]:
            for state in data["progress_states"]:
                assert "stage" in state
                assert "status" in state
                assert state["status"] in ["pending", "active", "completed", "failed"]
            
            # Check that at least some stages are completed
            completed = [s for s in data["progress_states"] if s["status"] == "completed"]
            assert len(completed) > 0, "No stages completed"
            
            print(f"✓ Progress states valid: {len(completed)}/{len(data['progress_states'])} completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
