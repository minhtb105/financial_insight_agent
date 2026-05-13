"""
Test script for streaming response functionality.

Tests the new /ask-stream endpoint with Server-Sent Events (SSE).
"""

import asyncio
import aiohttp
import json


async def test_streaming_endpoint():
    """Test the streaming endpoint."""
    print("=== Streaming Response Test ===")
    
    url = "http://localhost:8000/ask-stream"
    test_query = "VNM có bao nhiêu cổ phiếu đang lưu hành?"
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"Sending query: {test_query}")
            print("Streaming response:")
            print("-" * 50)
            
            async with session.post(url, json={"query": test_query}) as response:
                if response.status == 200:
                    # Process SSE stream
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data:'):
                            data = line[5:].strip()  # Remove 'data:' prefix
                            if data:
                                try:
                                    # Try to parse as JSON (final response)
                                    json_response = json.loads(data)
                                    if 'answer' in json_response:
                                        print(f"\n[FINAL] {json_response['answer']}")
                                        break
                                except json.JSONDecodeError:
                                    # Regular stream chunk
                                    print(data, end='', flush=True)
                else:
                    print(f"Error: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"Error response: {error_text}")
                    
    except Exception as e:
        print(f"Test failed: {e}")


async def test_regular_endpoint():
    """Test the regular endpoint for comparison."""
    print("\n=== Regular Response Test ===")
    
    url = "http://localhost:8000/ask"
    test_query = "VNM có bao nhiêu cổ phiếu đang lưu hành?"
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"Sending query: {test_query}")
            
            async with session.post(url, json={"query": test_query}) as response:
                if response.status == 200:
                    response_data = await response.json()
                    print(f"Response: {response_data['answer']}")
                else:
                    print(f"Error: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"Error response: {error_text}")
                    
    except Exception as e:
        print(f"Test failed: {e}")


async def main():
    """Run both streaming and regular tests."""
    print("Streaming Response Test Suite")
    print("=" * 50)
    
    # Test regular endpoint first
    await test_regular_endpoint()
    
    # Test streaming endpoint
    await test_streaming_endpoint()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nStreaming benefits:")
    print("- User sees response immediately")
    print("- Better UX for long responses")
    print("- Real-time feedback")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
    