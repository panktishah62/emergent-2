"""
AI Voice Calling Service for PriceHunter
Uses Bland.ai to call vendors and extract pricing information
"""

import asyncio
import httpx
import json
import logging
import random
import os
import uuid
from typing import Optional, Dict, List
from pydantic import BaseModel
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


class CallResult(BaseModel):
    """Result from a vendor call"""
    vendor_name: str
    vendor_phone: str
    product: str
    call_id: Optional[str] = None
    status: str  # "completed", "failed", "timeout", "mock"
    transcript: Optional[str] = None
    price: Optional[float] = None
    availability: bool = False
    negotiated: bool = False
    delivery_time: Optional[str] = None
    notes: str = ""
    confidence: float = 0.0
    call_duration: Optional[float] = None


class VoiceCallingService:
    """Service for making AI voice calls to vendors using Bland.ai"""
    
    def __init__(
        self,
        bland_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        webhook_url: Optional[str] = None,
        mock_mode: bool = True
    ):
        self.bland_api_key = bland_api_key
        self.openai_api_key = openai_api_key
        self.webhook_url = webhook_url
        self.mock_mode = mock_mode
        self.base_url = "https://api.bland.ai/v1"
        
        if not mock_mode and not bland_api_key:
            logger.warning("Bland.ai API key not provided, forcing mock mode")
            self.mock_mode = True
    
    def generate_mock_transcript(
        self,
        product: str,
        vendor_name: str,
        category: str
    ) -> Dict:
        """
        Generate realistic mock transcript for testing
        Returns transcript and extracted data
        """
        # Price ranges based on category
        price_ranges = {
            "groceries": (20, 500),
            "electronics": (5000, 150000),
            "medicine": (50, 2000),
            "clothing": (300, 5000),
            "hardware": (100, 10000),
            "general": (100, 5000),
        }
        
        min_price, max_price = price_ranges.get(category, (100, 5000))
        price = round(random.uniform(min_price, max_price) / 100) * 100
        
        # Realistic transcript templates
        transcripts = [
            f"Agent: Namaste, do you have {product} available?\n"
            f"Vendor: Haan ji, available hai.\n"
            f"Agent: What is the price?\n"
            f"Vendor: {price} rupees hai sir.\n"
            f"Agent: Any discount available?\n"
            f"Vendor: 5% off if you buy today. Otherwise full price.\n"
            f"Agent: Thank you. When can I pick it up?\n"
            f"Vendor: Abhi available hai, come anytime.",
            
            f"Agent: Hello, I'm calling to inquire about {product}. Do you have it?\n"
            f"Vendor: Yes sir, we have it in stock.\n"
            f"Agent: What's your price?\n"
            f"Vendor: It's {price} rupees.\n"
            f"Agent: Can you offer any discount?\n"
            f"Vendor: Sorry sir, fixed price only.\n"
            f"Agent: Okay, thank you.\n"
            f"Vendor: Welcome.",
            
            f"Agent: Hi, {product} milega?\n"
            f"Vendor: Ji haan, abhi stock mein hai.\n"
            f"Agent: Price kya hai?\n"
            f"Vendor: Rs. {price}.\n"
            f"Agent: Kuch discount de sakte ho?\n"
            f"Vendor: Thoda adjust kar sakte hain - {round(price * 0.95, 2)} mein de dunga.\n"
            f"Agent: Good, delivery ho jayega?\n"
            f"Vendor: Haan, local delivery kar denge.",
        ]
        
        transcript = random.choice(transcripts)
        
        # Extract data from mock transcript
        has_discount = "discount" in transcript.lower() or "off" in transcript.lower()
        has_delivery = "delivery" in transcript.lower() or "pick" in transcript.lower()
        
        delivery_options = [
            "Available for pickup now",
            "Local delivery available",
            "Same day delivery",
            "Pick up in 30 mins",
            "Delivery in 1-2 hours"
        ]
        
        return {
            "transcript": transcript,
            "price": price,
            "availability": True,
            "negotiated": has_discount and random.random() > 0.3,
            "delivery_time": random.choice(delivery_options) if has_delivery else None,
            "notes": f"Called {vendor_name}. Price quoted: ₹{price}.",
            "confidence": random.uniform(0.75, 0.95)
        }
    
    async def make_bland_call(
        self,
        vendor_phone: str,
        vendor_name: str,
        product: str,
        category: str
    ) -> Dict:
        """
        Make an outbound call via Bland.ai API
        Returns call_id and initial status
        """
        if not self.bland_api_key:
            raise ValueError("Bland.ai API key not configured")
        
        task = f"""You are calling a shop to inquire about a product. 
Ask if they have {product} in stock, what is their price, and if they can offer any discount. 
Be polite and professional. Speak in Hindi or English based on how the vendor responds. 
Keep the call under 60 seconds."""
        
        payload = {
            "phone_number": vendor_phone,
            "task": task,
            "voice": "maya",
            "wait_for_greeting": True,
            "record": True,
            "max_duration": 60,
            "metadata": {
                "vendor_name": vendor_name,
                "product": product,
                "vendor_phone": vendor_phone,
                "category": category
            }
        }
        
        # Add webhook if configured
        if self.webhook_url:
            payload["webhook"] = self.webhook_url
        
        headers = {
            "Authorization": self.bland_api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Initiating Bland.ai call to {vendor_name} ({vendor_phone})")
                
                response = await client.post(
                    f"{self.base_url}/calls",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                data = response.json()
                
                call_id = data.get("call_id")
                logger.info(f"Bland.ai call initiated: {call_id}")
                
                return {
                    "call_id": call_id,
                    "status": data.get("status", "initiated")
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Bland.ai API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error making Bland.ai call: {e}")
            raise
    
    async def poll_call_status(
        self,
        call_id: str,
        max_wait: int = 120,
        poll_interval: int = 5
    ) -> Dict:
        """
        Poll Bland.ai API for call completion
        Returns final call data with transcript
        """
        if not self.bland_api_key:
            raise ValueError("Bland.ai API key not configured")
        
        headers = {
            "Authorization": self.bland_api_key
        }
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with httpx.AsyncClient() as client:
                while True:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    if elapsed > max_wait:
                        logger.warning(f"Call {call_id} polling timeout after {max_wait}s")
                        return {
                            "status": "timeout",
                            "call_id": call_id,
                            "transcript": None
                        }
                    
                    logger.debug(f"Polling call {call_id}... ({elapsed:.1f}s)")
                    
                    response = await client.get(
                        f"{self.base_url}/calls/{call_id}",
                        headers=headers,
                        timeout=10.0
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    status = data.get("status")
                    
                    if status == "completed":
                        logger.info(f"Call {call_id} completed")
                        return data
                    elif status in ["failed", "no-answer", "busy", "cancelled"]:
                        logger.warning(f"Call {call_id} ended with status: {status}")
                        return data
                    
                    # Wait before next poll
                    await asyncio.sleep(poll_interval)
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"Error polling call {call_id}: {e.response.status_code}")
            return {
                "status": "failed",
                "call_id": call_id,
                "transcript": None
            }
        except Exception as e:
            logger.error(f"Unexpected error polling call {call_id}: {e}")
            return {
                "status": "failed",
                "call_id": call_id,
                "transcript": None
            }
    
    async def extract_data_from_transcript(
        self,
        transcript: str,
        product: str
    ) -> Dict:
        """
        Use OpenAI to extract structured data from call transcript
        Returns dict with price, availability, negotiated, delivery_time, notes, confidence
        """
        if not self.openai_api_key:
            logger.warning("OpenAI API key not configured, using fallback extraction")
            return {
                "price": None,
                "availability": False,
                "negotiated": False,
                "delivery_time": None,
                "notes": "Could not extract data - API key missing",
                "confidence": 0.5
            }
        
        system_message = f"""Given this phone call transcript between an AI agent and a shop vendor about {product}, extract:
- price: number in INR or null if not mentioned
- availability: boolean (true if vendor has the product)
- negotiated: whether discount was offered, boolean
- delivery_time: string describing when/how product can be obtained, or null
- notes: brief summary string (max 100 chars)
- confidence: your confidence in the extraction, 0.0 to 1.0

Return ONLY valid JSON with these exact keys. No additional text or explanation.

Example: {{"price": 15000, "availability": true, "negotiated": true, "delivery_time": "Same day pickup", "notes": "5% discount offered for immediate purchase", "confidence": 0.9}}"""
        
        try:
            chat = LlmChat(
                api_key=self.openai_api_key,
                session_id=str(uuid.uuid4()),
                system_message=system_message
            ).with_model("openai", "gpt-4o-mini")
            
            user_message = UserMessage(text=f"Transcript:\n{transcript}")
            
            response = await chat.send_message(user_message)
            
            # Parse JSON response
            extracted = json.loads(response.strip())
            
            logger.info(f"Extracted data from transcript: {extracted}")
            return extracted
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI extraction response: {e}")
            return {
                "price": None,
                "availability": "available" in transcript.lower() or "stock" in transcript.lower(),
                "negotiated": "discount" in transcript.lower(),
                "delivery_time": None,
                "notes": "Partial extraction - JSON parse error",
                "confidence": 0.6
            }
        except Exception as e:
            logger.error(f"Error extracting data from transcript: {e}")
            return {
                "price": None,
                "availability": False,
                "negotiated": False,
                "delivery_time": None,
                "notes": f"Extraction error: {str(e)[:50]}",
                "confidence": 0.4
            }
    
    async def call_vendor(
        self,
        vendor_name: str,
        vendor_phone: str,
        product: str,
        category: str,
        max_wait: int = 120
    ) -> CallResult:
        """
        Complete flow: make call, wait for completion, extract data
        Returns CallResult with all extracted information
        
        Args:
            max_wait: Maximum seconds to wait for call completion (default 120)
        """
        # MOCK MODE: Generate mock transcript
        if self.mock_mode:
            logger.info(f"MOCK MODE: Simulating call to {vendor_name}")
            
            # Simulate some delay
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            mock_data = self.generate_mock_transcript(product, vendor_name, category)
            
            return CallResult(
                vendor_name=vendor_name,
                vendor_phone=vendor_phone,
                product=product,
                call_id=f"mock_{uuid.uuid4().hex[:8]}",
                status="mock",
                transcript=mock_data["transcript"],
                price=mock_data["price"],
                availability=mock_data["availability"],
                negotiated=mock_data["negotiated"],
                delivery_time=mock_data["delivery_time"],
                notes=mock_data["notes"],
                confidence=mock_data["confidence"],
                call_duration=random.randint(30, 60)
            )
        
        # REAL MODE: Make actual Bland.ai call
        try:
            # Step 1: Initiate call
            call_data = await self.make_bland_call(
                vendor_phone,
                vendor_name,
                product,
                category
            )
            
            call_id = call_data["call_id"]
            
            # Step 2: Poll for completion with configurable timeout
            final_data = await self.poll_call_status(call_id, max_wait=max_wait)
            
            status = final_data.get("status")
            transcript = final_data.get("concatenated_transcript")
            
            if status != "completed" or not transcript:
                logger.warning(f"Call {call_id} did not complete successfully: {status}")
                return CallResult(
                    vendor_name=vendor_name,
                    vendor_phone=vendor_phone,
                    product=product,
                    call_id=call_id,
                    status=status,
                    transcript=transcript,
                    notes=f"Call {status}",
                    confidence=0.0
                )
            
            # Step 3: Extract data from transcript
            extracted = await self.extract_data_from_transcript(transcript, product)
            
            return CallResult(
                vendor_name=vendor_name,
                vendor_phone=vendor_phone,
                product=product,
                call_id=call_id,
                status="completed",
                transcript=transcript,
                price=extracted.get("price"),
                availability=extracted.get("availability", False),
                negotiated=extracted.get("negotiated", False),
                delivery_time=extracted.get("delivery_time"),
                notes=extracted.get("notes", ""),
                confidence=extracted.get("confidence", 0.7),
                call_duration=final_data.get("call_length")
            )
            
        except Exception as e:
            logger.error(f"Error in complete call flow for {vendor_name}: {e}")
            return CallResult(
                vendor_name=vendor_name,
                vendor_phone=vendor_phone,
                product=product,
                status="failed",
                notes=f"Call failed: {str(e)[:50]}",
                confidence=0.0
            )
    
    async def call_multiple_vendors(
        self,
        vendors: List[Dict],
        product: str,
        category: str,
        sequential: bool = False,
        delay_between_calls: int = 5
    ) -> List[CallResult]:
        """
        Call multiple vendors concurrently OR sequentially
        
        Args:
            vendors: List of dicts with 'name' and 'phone_number' keys
            product: Product to inquire about
            category: Product category
            sequential: If True, calls one at a time (for rate limits)
            delay_between_calls: Seconds to wait between sequential calls
        
        Returns:
            List of CallResult objects
        """
        logger.info(f"Starting {'sequential' if sequential else 'concurrent'} calls to {len(vendors)} vendors")
        
        if sequential:
            # SEQUENTIAL MODE: Call one vendor at a time
            results = []
            for i, vendor in enumerate(vendors, 1):
                if not vendor.get("phone_number"):
                    logger.warning(f"Skipping {vendor.get('name')} - no phone number")
                    continue
                
                logger.info(f"[{i}/{len(vendors)}] Calling {vendor['name']} sequentially...")
                
                try:
                    result = await self.call_vendor(
                        vendor["name"],
                        vendor["phone_number"],
                        product,
                        category
                    )
                    results.append(result)
                    
                    logger.info(
                        f"[{i}/{len(vendors)}] Completed: {result.status} "
                        f"(price: {result.price}, confidence: {result.confidence})"
                    )
                    
                    # Wait before next call (except after last one)
                    if i < len(vendors) and delay_between_calls > 0:
                        logger.info(f"Waiting {delay_between_calls}s before next call...")
                        await asyncio.sleep(delay_between_calls)
                        
                except Exception as e:
                    logger.error(f"[{i}/{len(vendors)}] Error calling {vendor['name']}: {e}")
                    # Create failed result but continue with next vendor
                    results.append(CallResult(
                        vendor_name=vendor["name"],
                        vendor_phone=vendor["phone_number"],
                        product=product,
                        status="failed",
                        notes=f"Error: {str(e)[:50]}",
                        confidence=0.0
                    ))
            
            logger.info(f"Sequential calls completed: {len(results)} vendors called")
            return results
            
        else:
            # CONCURRENT MODE: Call all vendors simultaneously (original behavior)
            tasks = [
                self.call_vendor(
                    vendor["name"],
                    vendor["phone_number"],
                    product,
                    category
                )
                for vendor in vendors
                if vendor.get("phone_number")
            ]
            
            # Run all calls concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and collect successful results
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Vendor call {i} raised exception: {result}")
                    continue
                successful_results.append(result)
            
            logger.info(
                f"Completed {len(successful_results)}/{len(vendors)} vendor calls successfully"
            )
            
            return successful_results


# Convenience function
async def call_vendors_for_pricing(
    vendors: List[Dict],
    product: str,
    category: str,
    bland_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    mock_mode: bool = True,
    sequential: bool = False,
    delay_between_calls: int = 5
) -> List[CallResult]:
    """
    Convenience function to call vendors and get pricing
    
    Args:
        sequential: If True, calls one vendor at a time (recommended for rate limits)
        delay_between_calls: Seconds to wait between sequential calls
    
    Returns list of CallResult objects
    """
    service = VoiceCallingService(
        bland_api_key=bland_api_key,
        openai_api_key=openai_api_key,
        mock_mode=mock_mode
    )
    
    return await service.call_multiple_vendors(
        vendors, 
        product, 
        category,
        sequential=sequential,
        delay_between_calls=delay_between_calls
    )
