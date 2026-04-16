"""
Backend API Tests for PriceHunter Chat Endpoints - Staged Flow
Tests: POST /api/chat/message (with discovered_vendors, progress_states), POST /api/chat/reset, GET /api/health
Key features: Staged display flow with vendor list, progress animation, then results
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


class TestChatMessageBasic:
    """Basic tests for POST /api/chat/message endpoint"""
    
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


class TestStagedFlowDiscoveredVendors:
    """Tests for STAGED flow: discovered_vendors array with name and phone"""
    
    def test_search_returns_discovered_vendors(self):
        """Test that search returns discovered_vendors array with name and phone"""
        session_id = f"test_vendors_{uuid.uuid4()}"
        
        # Add delay to avoid LLM rate limits
        time.sleep(5)
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "cheapest iPhone 15 in Bangalore"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify search was triggered
        assert data["search_triggered"] == True
        
        # CRITICAL: Verify discovered_vendors array exists
        assert "discovered_vendors" in data, "Missing discovered_vendors in response"
        
        if data["discovered_vendors"]:
            assert len(data["discovered_vendors"]) > 0, "discovered_vendors is empty"
            
            # Verify each vendor has name and phone
            for vendor in data["discovered_vendors"]:
                assert "name" in vendor, f"Vendor missing 'name': {vendor}"
                assert "phone" in vendor, f"Vendor missing 'phone': {vendor}"
                assert len(vendor["name"]) > 0, "Vendor name is empty"
                # Phone can be "N/A" but should exist
                assert vendor["phone"] is not None, "Vendor phone is None"
            
            print(f"✓ discovered_vendors: {len(data['discovered_vendors'])} vendors found")
            print(f"  Sample: {data['discovered_vendors'][0]['name']} - {data['discovered_vendors'][0]['phone']}")
        else:
            print("⚠ discovered_vendors is empty (may be expected if no vendors found)")
    
    def test_discovered_vendors_have_address(self):
        """Test that discovered_vendors include address field"""
        session_id = f"test_addr_{uuid.uuid4()}"
        
        time.sleep(5)
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "tomatoes near Rajkot"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("discovered_vendors"):
            for vendor in data["discovered_vendors"]:
                assert "address" in vendor, f"Vendor missing 'address': {vendor}"
            
            print(f"✓ All {len(data['discovered_vendors'])} vendors have address field")


class TestStagedFlowProgressStates:
    """Tests for STAGED flow: progress_states with per-vendor 'Contacting X' entries"""
    
    def test_progress_states_include_vendor_contacts(self):
        """Test that progress_states include 'Contacting X' for each discovered vendor"""
        session_id = f"test_progress_{uuid.uuid4()}"
        
        time.sleep(5)
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "cheapest iPhone 15 in Bangalore"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["search_triggered"] == True
        assert "progress_states" in data
        assert "discovered_vendors" in data
        
        if data["progress_states"] and data["discovered_vendors"]:
            # Extract stages that start with "Contacting"
            contacting_stages = [s for s in data["progress_states"] if s["stage"].startswith("Contacting")]
            
            # Should have at least some "Contacting X" stages
            assert len(contacting_stages) > 0, "No 'Contacting X' stages found in progress_states"
            
            # Each contacting stage should have vendor name
            for stage in contacting_stages:
                assert "Contacting" in stage["stage"]
                # Detail should contain phone number
                if stage.get("detail"):
                    print(f"  Stage: {stage['stage']} - {stage['detail']}")
            
            print(f"✓ progress_states has {len(contacting_stages)} 'Contacting X' entries")
    
    def test_progress_states_structure(self):
        """Test progress states have correct structure with stage, status, detail"""
        session_id = f"test_pstruct_{uuid.uuid4()}"
        
        time.sleep(5)
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "laptop under 50000 in Mumbai"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["progress_states"]:
            for state in data["progress_states"]:
                assert "stage" in state, f"Missing 'stage' in progress state: {state}"
                assert "status" in state, f"Missing 'status' in progress state: {state}"
                assert state["status"] in ["pending", "active", "completed", "failed"], f"Invalid status: {state['status']}"
            
            # Check expected stages exist
            stages = [s["stage"] for s in data["progress_states"]]
            assert "Understanding your request" in stages, "Missing 'Understanding your request' stage"
            assert "Searching online platforms" in stages, "Missing 'Searching online platforms' stage"
            
            # Check that at least some stages are completed
            completed = [s for s in data["progress_states"] if s["status"] == "completed"]
            assert len(completed) > 0, "No stages completed"
            
            print(f"✓ Progress states valid: {len(completed)}/{len(data['progress_states'])} completed")
            print(f"  Stages: {stages[:5]}...")


class TestSearchResultsStructure:
    """Tests for search results data structure and values"""
    
    def test_results_have_required_fields(self):
        """Test that all results have required fields including rank, source_type, vendor_name, price, delivery_time, availability, confidence"""
        session_id = f"test_fields_{uuid.uuid4()}"
        
        time.sleep(5)
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "nearest pharmacy in Delhi"
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
                
                # Verify data types
                assert isinstance(result["rank"], int), f"rank should be int: {result['rank']}"
                assert result["source_type"] in ["ONLINE", "OFFLINE"], f"Invalid source_type: {result['source_type']}"
                assert isinstance(result["price"], (int, float)), f"price should be numeric: {result['price']}"
                assert isinstance(result["confidence"], (int, float)), f"confidence should be numeric: {result['confidence']}"
                assert 0 <= result["confidence"] <= 1, f"confidence out of range: {result['confidence']}"
            
            print(f"✓ All {len(data['results'])} results have required fields with correct types")
    
    def test_results_ranking_order(self):
        """Test that results are ranked in order starting from 1"""
        session_id = f"test_rank_{uuid.uuid4()}"
        
        time.sleep(5)
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "cheapest laptop in Chennai"
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


class TestSearchMetadata:
    """Tests for search_metadata in response"""
    
    def test_search_metadata_structure(self):
        """Test search_metadata has total_results, online_count, offline_count, search_time"""
        session_id = f"test_meta_{uuid.uuid4()}"
        
        time.sleep(5)
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "cheapest iPhone 15 in Bangalore"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["search_triggered"] == True
        assert "search_metadata" in data
        
        if data["search_metadata"]:
            meta = data["search_metadata"]
            assert "total_results" in meta, "Missing total_results in search_metadata"
            assert "online_count" in meta, "Missing online_count in search_metadata"
            assert "offline_count" in meta, "Missing offline_count in search_metadata"
            assert "search_time" in meta, "Missing search_time in search_metadata"
            
            # Verify counts add up
            if data["results"]:
                assert meta["total_results"] == len(data["results"]), "total_results mismatch"
            
            print(f"✓ search_metadata: {meta['total_results']} results ({meta['online_count']} online, {meta['offline_count']} offline) in {meta['search_time']}s")


class TestConversationalFlow:
    """Tests for conversational flow - partial queries should prompt for more info"""
    
    def test_partial_query_asks_for_location(self):
        """Test that partial query (product only) prompts for location before searching"""
        session_id = f"test_conv_{uuid.uuid4()}"
        
        response = requests.post(f"{BASE_URL}/api/chat/message", json={
            "session_id": session_id,
            "message": "I need a laptop"
        }, timeout=60)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should NOT trigger search yet (no location)
        assert data["search_triggered"] == False, "Search should not trigger without location"
        assert data["conversation_state"] == "collecting"
        
        # discovered_vendors should be empty or not present
        if "discovered_vendors" in data:
            assert len(data.get("discovered_vendors", [])) == 0, "Should not have discovered_vendors without search"
        
        print(f"✓ Partial query correctly does NOT trigger search")
        print(f"  Assistant: {data['assistant_message'][:100]}...")


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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
