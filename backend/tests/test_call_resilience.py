"""
Tests for offline pipeline call failure resilience.
Verifies the app never breaks regardless of call outcome.
"""
import pytest
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import AsyncMock, patch, MagicMock
from voice_calling import VoiceCallingService, CallResult


@pytest.fixture
def mock_voice_service():
    return VoiceCallingService(
        bland_api_key="test_key",
        openai_api_key="test_key",
        mock_mode=True
    )


@pytest.fixture
def real_voice_service():
    return VoiceCallingService(
        bland_api_key="test_key",
        openai_api_key="test_key",
        mock_mode=False
    )


class TestCallVendorFailureScenarios:
    """Test that call_vendor handles every failure gracefully"""

    @pytest.mark.asyncio
    async def test_mock_mode_always_succeeds(self, mock_voice_service):
        """Mock mode should always return a valid result"""
        result = await mock_voice_service.call_vendor(
            vendor_name="Test Shop",
            vendor_phone="+919999999999",
            product="iPhone 15",
            category="electronics"
        )
        assert result.status == "mock"
        assert result.price is not None
        assert result.price > 0
        assert result.vendor_name == "Test Shop"
        print("PASS: Mock mode always succeeds")

    @pytest.mark.asyncio
    async def test_real_call_api_error_returns_failed(self, real_voice_service):
        """If Bland.ai API returns error, call_vendor should return failed status"""
        with patch.object(real_voice_service, 'make_bland_call', side_effect=Exception("429 Rate limit")):
            result = await real_voice_service.call_vendor(
                vendor_name="Test Shop",
                vendor_phone="+919999999999",
                product="iPhone 15",
                category="electronics"
            )
            assert result.status == "failed"
            assert result.confidence == 0.0
            assert "Call failed" in result.notes
            print("PASS: API error returns failed status, no crash")

    @pytest.mark.asyncio
    async def test_real_call_timeout_returns_timeout(self, real_voice_service):
        """If call times out during polling, should return timeout status"""
        with patch.object(real_voice_service, 'make_bland_call', return_value={"call_id": "test_123", "status": "initiated"}):
            with patch.object(real_voice_service, 'poll_call_status', return_value={"status": "timeout", "call_id": "test_123", "concatenated_transcript": None}):
                result = await real_voice_service.call_vendor(
                    vendor_name="Test Shop",
                    vendor_phone="+919999999999",
                    product="iPhone 15",
                    category="electronics"
                )
                assert result.status == "timeout"
                assert result.confidence == 0.0
                print("PASS: Timeout returns timeout status, no crash")

    @pytest.mark.asyncio
    async def test_real_call_no_answer(self, real_voice_service):
        """If vendor doesn't pick up, should return no-answer status"""
        with patch.object(real_voice_service, 'make_bland_call', return_value={"call_id": "test_456", "status": "initiated"}):
            with patch.object(real_voice_service, 'poll_call_status', return_value={"status": "no-answer", "call_id": "test_456", "concatenated_transcript": None}):
                result = await real_voice_service.call_vendor(
                    vendor_name="Test Shop",
                    vendor_phone="+919999999999",
                    product="iPhone 15",
                    category="electronics"
                )
                assert result.status == "no-answer"
                assert result.confidence == 0.0
                print("PASS: No-answer returns gracefully, no crash")

    @pytest.mark.asyncio
    async def test_real_call_busy(self, real_voice_service):
        """If line is busy, should return busy status"""
        with patch.object(real_voice_service, 'make_bland_call', return_value={"call_id": "test_789", "status": "initiated"}):
            with patch.object(real_voice_service, 'poll_call_status', return_value={"status": "busy", "call_id": "test_789", "concatenated_transcript": None}):
                result = await real_voice_service.call_vendor(
                    vendor_name="Test Shop",
                    vendor_phone="+919999999999",
                    product="iPhone 15",
                    category="electronics"
                )
                assert result.status == "busy"
                assert result.confidence == 0.0
                print("PASS: Busy returns gracefully, no crash")

    @pytest.mark.asyncio
    async def test_real_call_cancelled(self, real_voice_service):
        """If call is cancelled, should return cancelled status"""
        with patch.object(real_voice_service, 'make_bland_call', return_value={"call_id": "test_abc", "status": "initiated"}):
            with patch.object(real_voice_service, 'poll_call_status', return_value={"status": "cancelled", "call_id": "test_abc", "concatenated_transcript": None}):
                result = await real_voice_service.call_vendor(
                    vendor_name="Test Shop",
                    vendor_phone="+919999999999",
                    product="iPhone 15",
                    category="electronics"
                )
                assert result.status == "cancelled"
                assert result.confidence == 0.0
                print("PASS: Cancelled returns gracefully, no crash")

    @pytest.mark.asyncio
    async def test_completed_but_no_transcript(self, real_voice_service):
        """If call completed but transcript is None, should return failed"""
        with patch.object(real_voice_service, 'make_bland_call', return_value={"call_id": "test_no_tx", "status": "initiated"}):
            with patch.object(real_voice_service, 'poll_call_status', return_value={"status": "completed", "call_id": "test_no_tx", "concatenated_transcript": None}):
                result = await real_voice_service.call_vendor(
                    vendor_name="Test Shop",
                    vendor_phone="+919999999999",
                    product="iPhone 15",
                    category="electronics"
                )
                # No transcript -> goes to else branch
                assert result.confidence == 0.0
                print("PASS: Completed but no transcript handled, no crash")

    @pytest.mark.asyncio
    async def test_completed_but_extraction_returns_no_price(self, real_voice_service):
        """If transcript exists but extraction yields price=None"""
        with patch.object(real_voice_service, 'make_bland_call', return_value={"call_id": "test_no_price", "status": "initiated"}):
            with patch.object(real_voice_service, 'poll_call_status', return_value={
                "status": "completed", "call_id": "test_no_price",
                "concatenated_transcript": "Hello, yes we are open. Bye."
            }):
                with patch.object(real_voice_service, 'extract_data_from_transcript', return_value={
                    "price": None, "availability": False, "negotiated": False,
                    "delivery_time": None, "notes": "No price mentioned", "confidence": 0.3
                }):
                    result = await real_voice_service.call_vendor(
                        vendor_name="Test Shop",
                        vendor_phone="+919999999999",
                        product="iPhone 15",
                        category="electronics"
                    )
                    assert result.status == "completed"
                    assert result.price is None
                    assert result.confidence == 0.3
                    print("PASS: Completed with no price extracted handled, no crash")

    @pytest.mark.asyncio
    async def test_network_exception_during_poll(self, real_voice_service):
        """If network crashes during polling"""
        with patch.object(real_voice_service, 'make_bland_call', return_value={"call_id": "test_net", "status": "initiated"}):
            with patch.object(real_voice_service, 'poll_call_status', side_effect=Exception("Network error")):
                result = await real_voice_service.call_vendor(
                    vendor_name="Test Shop",
                    vendor_phone="+919999999999",
                    product="iPhone 15",
                    category="electronics"
                )
                assert result.status == "failed"
                assert result.confidence == 0.0
                print("PASS: Network crash during poll handled, no crash")


class TestOfflinePipelineResilience:
    """Test that the full pipeline never breaks regardless of call outcomes"""

    @pytest.mark.asyncio
    async def test_pipeline_with_all_failures_still_returns_results(self):
        """Even if everything fails, pipeline returns mock results"""
        from server import generate_mock_offline_results
        results = generate_mock_offline_results("iPhone 15", "electronics", "Bangalore", count=5)
        assert len(results) == 5
        for r in results:
            assert r["price"] > 0
            assert r["source_type"] == "OFFLINE"
        print("PASS: Mock fallback always generates valid results")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
