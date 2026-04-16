"""
Backend API Tests for PriceHunter Payment Endpoints (Razorpay Integration)
Tests: POST /api/payments/create-order, POST /api/payments/verify, GET /api/payments/status/{session_id}
Key features: Razorpay Standard Checkout paywall for Rs 99 premium upgrade
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPaymentCreateOrder:
    """Tests for POST /api/payments/create-order endpoint"""
    
    def test_create_order_returns_correct_structure(self):
        """Test create-order returns order_id, amount=9900, currency=INR, key_id"""
        session_id = f"test_payment_{uuid.uuid4()}"
        
        response = requests.post(f"{BASE_URL}/api/payments/create-order", json={
            "session_id": session_id
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "order_id" in data, "Missing order_id in response"
        assert "amount" in data, "Missing amount in response"
        assert "currency" in data, "Missing currency in response"
        assert "key_id" in data, "Missing key_id in response"
        
        # Verify values
        assert data["amount"] == 9900, f"Expected amount 9900 (Rs 99 in paise), got {data['amount']}"
        assert data["currency"] == "INR", f"Expected currency INR, got {data['currency']}"
        assert data["order_id"].startswith("order_"), f"order_id should start with 'order_': {data['order_id']}"
        assert data["key_id"].startswith("rzp_"), f"key_id should start with 'rzp_': {data['key_id']}"
        
        print(f"✓ create-order: order_id={data['order_id']}, amount={data['amount']}, currency={data['currency']}, key_id={data['key_id'][:15]}...")
    
    def test_create_order_without_session_id(self):
        """Test create-order works without session_id (optional field)"""
        response = requests.post(f"{BASE_URL}/api/payments/create-order", json={})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "order_id" in data
        assert data["amount"] == 9900
        print(f"✓ create-order without session_id: order_id={data['order_id']}")
    
    def test_create_order_generates_unique_order_ids(self):
        """Test that each create-order call generates a unique order_id"""
        order_ids = []
        
        for i in range(3):
            response = requests.post(f"{BASE_URL}/api/payments/create-order", json={
                "session_id": f"test_unique_{i}_{uuid.uuid4()}"
            })
            assert response.status_code == 200
            order_ids.append(response.json()["order_id"])
        
        # All order_ids should be unique
        assert len(order_ids) == len(set(order_ids)), f"Order IDs not unique: {order_ids}"
        print(f"✓ Generated 3 unique order_ids: {order_ids}")


class TestPaymentVerify:
    """Tests for POST /api/payments/verify endpoint"""
    
    def test_verify_rejects_invalid_signature(self):
        """Test verify endpoint rejects invalid Razorpay signature with 400"""
        response = requests.post(f"{BASE_URL}/api/payments/verify", json={
            "razorpay_order_id": "order_test123",
            "razorpay_payment_id": "pay_test123",
            "razorpay_signature": "invalid_signature_abc123",
            "session_id": "test_session_verify"
        })
        
        assert response.status_code == 400, f"Expected 400 for invalid signature, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "verification failed" in data["detail"].lower() or "failed" in data["detail"].lower()
        print(f"✓ verify correctly rejects invalid signature: {data['detail']}")
    
    def test_verify_requires_all_fields(self):
        """Test verify endpoint requires razorpay_order_id, razorpay_payment_id, razorpay_signature"""
        # Missing razorpay_order_id
        response = requests.post(f"{BASE_URL}/api/payments/verify", json={
            "razorpay_payment_id": "pay_test123",
            "razorpay_signature": "sig_test123"
        })
        assert response.status_code == 422, f"Expected 422 for missing field, got {response.status_code}"
        
        # Missing razorpay_payment_id
        response = requests.post(f"{BASE_URL}/api/payments/verify", json={
            "razorpay_order_id": "order_test123",
            "razorpay_signature": "sig_test123"
        })
        assert response.status_code == 422, f"Expected 422 for missing field, got {response.status_code}"
        
        # Missing razorpay_signature
        response = requests.post(f"{BASE_URL}/api/payments/verify", json={
            "razorpay_order_id": "order_test123",
            "razorpay_payment_id": "pay_test123"
        })
        assert response.status_code == 422, f"Expected 422 for missing field, got {response.status_code}"
        
        print("✓ verify correctly requires all mandatory fields")
    
    def test_verify_with_empty_signature(self):
        """Test verify rejects empty signature"""
        response = requests.post(f"{BASE_URL}/api/payments/verify", json={
            "razorpay_order_id": "order_test123",
            "razorpay_payment_id": "pay_test123",
            "razorpay_signature": "",
            "session_id": "test_empty_sig"
        })
        
        # Should fail verification (400) or validation (422)
        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"
        print(f"✓ verify rejects empty signature with status {response.status_code}")


class TestPaymentStatus:
    """Tests for GET /api/payments/status/{session_id} endpoint"""
    
    def test_status_returns_is_premium_false_for_unpaid(self):
        """Test status returns is_premium=false for unpaid session"""
        session_id = f"test_unpaid_{uuid.uuid4()}"
        
        response = requests.get(f"{BASE_URL}/api/payments/status/{session_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "is_premium" in data, "Missing is_premium in response"
        assert data["is_premium"] == False, f"Expected is_premium=False for unpaid, got {data['is_premium']}"
        
        print(f"✓ status for unpaid session: is_premium={data['is_premium']}")
    
    def test_status_returns_is_premium_false_for_nonexistent_session(self):
        """Test status returns is_premium=false for non-existent session"""
        response = requests.get(f"{BASE_URL}/api/payments/status/nonexistent_session_xyz123")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["is_premium"] == False
        print(f"✓ status for non-existent session: is_premium={data['is_premium']}")
    
    def test_status_after_order_creation_still_unpaid(self):
        """Test that creating an order doesn't mark session as premium (payment not completed)"""
        session_id = f"test_order_status_{uuid.uuid4()}"
        
        # Create order
        create_response = requests.post(f"{BASE_URL}/api/payments/create-order", json={
            "session_id": session_id
        })
        assert create_response.status_code == 200
        
        # Check status - should still be unpaid
        status_response = requests.get(f"{BASE_URL}/api/payments/status/{session_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        
        assert data["is_premium"] == False, "Session should not be premium after order creation (before payment)"
        print(f"✓ status after order creation (before payment): is_premium={data['is_premium']}")


class TestPaymentIntegrationFlow:
    """Integration tests for the full payment flow"""
    
    def test_full_payment_flow_order_creation(self):
        """Test the full flow: create order -> verify status is unpaid"""
        session_id = f"test_flow_{uuid.uuid4()}"
        
        # Step 1: Create order
        create_response = requests.post(f"{BASE_URL}/api/payments/create-order", json={
            "session_id": session_id
        })
        assert create_response.status_code == 200
        order_data = create_response.json()
        
        assert order_data["amount"] == 9900
        assert order_data["currency"] == "INR"
        order_id = order_data["order_id"]
        
        # Step 2: Check status (should be unpaid)
        status_response = requests.get(f"{BASE_URL}/api/payments/status/{session_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        assert status_data["is_premium"] == False
        
        # Step 3: Try to verify with invalid signature (should fail)
        verify_response = requests.post(f"{BASE_URL}/api/payments/verify", json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_fake_123",
            "razorpay_signature": "fake_signature_abc",
            "session_id": session_id
        })
        assert verify_response.status_code == 400
        
        # Step 4: Status should still be unpaid after failed verification
        status_response2 = requests.get(f"{BASE_URL}/api/payments/status/{session_id}")
        assert status_response2.status_code == 200
        assert status_response2.json()["is_premium"] == False
        
        print(f"✓ Full payment flow test passed: order_id={order_id}, status remains unpaid after failed verification")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
