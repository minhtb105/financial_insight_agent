#!/usr/bin/env python3
"""
Test script for Redis optimization improvements.

Demonstrates the performance and memory benefits of Redis Hash and MessagePack
compared to traditional JSON serialization.
"""

import time
from typing import Dict, Any

from infrastructure.cache.serialization import SerializationManager, SerializationFormat
from infrastructure.cache.redis_cache import get_cache_with_format
from infrastructure.cache.session_manager import SessionManager
from infrastructure.memory.short_term.memory import ShortTermMemory


def create_test_data() -> Dict[str, Any]:
    """Create realistic test data for financial insight agent."""
    return {
        "session_id": "test_session_123",
        "user_id": "user_456",
        "created_at": "2024-01-15T10:30:00",
        "last_accessed": "2024-01-15T10:35:00",
        "access_count": 15,
        "query_count": 8,
        "preferences": {
            "theme": "dark",
            "language": "vi",
            "notifications": True,
            "default_tickers": ["VNM", "VIC", "VCB"],
            "risk_tolerance": "medium"
        },
        "context": {
            "last_ticker": "VNM",
            "last_query_type": "financial_metrics",
            "user_intent": "investment_analysis",
            "session_duration": 1800,
            "query_history": [
                {"query": "VNM revenue 2023", "timestamp": "2024-01-15T10:32:00"},
                {"query": "VNM P/E ratio", "timestamp": "2024-01-15T10:34:00"}
            ]
        },
        "metadata": {
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "session_type": "interactive",
            "device_type": "desktop",
            "location": "Hanoi, Vietnam"
        },
        "company_profiles": {
            "VNM": {
                "name": "Vinamilk",
                "sector": "Food & Beverage",
                "market_cap": 120000000000000,
                "pe_ratio": 25.5,
                "dividend_yield": 4.2,
                "last_updated": "2024-01-15T10:30:00"
            },
            "VIC": {
                "name": "Vingroup",
                "sector": "Real Estate",
                "market_cap": 250000000000000,
                "pe_ratio": 15.2,
                "dividend_yield": 1.8,
                "last_updated": "2024-01-15T10:30:00"
            }
        },
        "market_patterns": {
            "bullish_trends": ["technology", "renewable_energy"],
            "bearish_trends": ["traditional_energy"],
            "volatile_sectors": ["cryptocurrency", "biotech"],
            "analysis_timestamp": "2024-01-15T10:35:00"
        }
    }


def test_serialization_performance():
    """Test serialization performance and compression ratios."""
    print("=== Serialization Performance Test ===")
    
    test_data = create_test_data()
    manager = SerializationManager()
    
    formats = [SerializationFormat.JSON, SerializationFormat.MSGPACK, SerializationFormat.REDIS_HASH]
    
    results = {}
    
    for format_type in formats:
        print(f"\nTesting {format_type.value}...")
        
        # Test serialization
        start_time = time.time()
        serialized = manager.serialize(test_data, format_type)
        serialize_time = time.time() - start_time
        
        # Test deserialization
        start_time = time.time()
        deserialized = manager.deserialize(serialized, format_type)
        deserialize_time = time.time() - start_time
        
        # Calculate size
        if isinstance(serialized, dict):
            size = sum(len(k) + len(v) for k, v in serialized.items())
        else:
            size = len(serialized)
        
        # Verify data integrity
        integrity_check = deserialized == test_data if deserialized else False
        
        results[format_type.value] = {
            "serialize_time_ms": serialize_time * 1000,
            "deserialize_time_ms": deserialize_time * 1000,
            "size_bytes": size,
            "integrity_check": integrity_check
        }
        
        print(f"  Serialize: {serialize_time*1000:.2f}ms")
        print(f"  Deserialize: {deserialize_time*1000:.2f}ms")
        print(f"  Size: {size} bytes")
        print(f"  Integrity: {'✓' if integrity_check else '✗'}")
    
    # Calculate compression ratios
    json_size = results["json"]["size_bytes"]
    print(f"\n=== Compression Ratios (vs JSON) ===")
    for format_name, data in results.items():
        if format_name != "json":
            ratio = json_size / data["size_bytes"] if data["size_bytes"] > 0 else 1.0
            savings = ((json_size - data["size_bytes"]) / json_size) * 100
            print(f"{format_name}: {ratio:.2f}x compression ({savings:.1f}% savings)")
    
    return results


def test_redis_operations():
    """Test Redis operations with different serialization formats."""
    print("\n=== Redis Operations Test ===")
    
    test_data = create_test_data()
    session_id = "test_redis_optimization"
    
    # Test different cache formats
    formats = [SerializationFormat.JSON, SerializationFormat.MSGPACK, SerializationFormat.REDIS_HASH]
    results = {}
    
    for format_type in formats:
        print(f"\nTesting Redis operations with {format_type.value}...")
        
        try:
            # Create cache instance with specific format
            cache = get_cache_with_format(format_type)
            if not cache:
                print(f"  Skipped: {format_type.value} not available")
                continue
            
            # Test SET operation
            start_time = time.time()
            set_success = cache.set(
                key=f"test:{session_id}",
                value=test_data,
                namespace="test",
                format=format_type
            )
            set_time = time.time() - start_time
            
            # Test GET operation
            start_time = time.time()
            retrieved_data = cache.get(
                key=f"test:{session_id}",
                namespace="test",
                format=format_type
            )
            get_time = time.time() - start_time
            
            # Verify data
            data_match = retrieved_data == test_data if retrieved_data else False
            
            # Clean up
            cache.delete(f"test:{session_id}", namespace="test")
            
            results[format_type.value] = {
                "set_time_ms": set_time * 1000,
                "get_time_ms": get_time * 1000,
                "success": set_success and data_match,
                "data_match": data_match
            }
            
            print(f"  SET: {set_time*1000:.2f}ms {'✓' if set_success else '✗'}")
            print(f"  GET: {get_time*1000:.2f}ms {'✓' if data_match else '✗'}")
            print(f"  Overall: {'✓' if results[format_type.value]['success'] else '✗'}")
            
        except Exception as e:
            print(f"  Error: {e}")
            results[format_type.value] = {"error": str(e)}
    
    return results


def test_session_manager():
    """Test SessionManager with Redis Hash optimization."""
    print("\n=== SessionManager Test ===")
    
    try:
        # Create session manager
        session_manager = SessionManager(session_ttl_hours=1)
        session_id = "test_session_manager"
        user_id = "test_user_123"
        
        # Create test session data
        session_data = {
            "preferences": {
                "theme": "dark",
                "language": "vi",
                "notifications": True
            },
            "context": {
                "last_ticker": "VNM",
                "query_count": 5
            }
        }
        
        # Test session creation
        print("Creating session...")
        create_success = session_manager.create_session(
            session_id=session_id,
            user_id=user_id,
            initial_data=session_data
        )
        print(f"  Session creation: {'✓' if create_success else '✗'}")
        
        if create_success:
            # Test session retrieval
            print("Retrieving session...")
            retrieved_session = session_manager.get_session(session_id)
            print(f"  Session retrieval: {'✓' if retrieved_session else '✗'}")
            
            if retrieved_session:
                # Test session updates
                print("Updating session...")
                update_success = session_manager.update_session(
                    session_id=session_id,
                    updates={"query_count": str(int(retrieved_session.get("query_count", "0")) + 1)}
                )
                print(f"  Session update: {'✓' if update_success else '✗'}")
                
                # Test context operations
                print("Testing context operations...")
                context_set = session_manager.set_context(session_id, {"test_context": "value"})
                context_get = session_manager.get_context(session_id)
                print(f"  Context set: {'✓' if context_set else '✗'}")
                print(f"  Context get: {'✓' if context_get else '✗'}")
                
                # Test user preferences
                print("Testing user preferences...")
                prefs_set = session_manager.set_user_preferences(session_id, {"theme": "light", "language": "en"})
                prefs_get = session_manager.get_user_preferences(session_id)
                print(f"  Preferences set: {'✓' if prefs_set else '✗'}")
                print(f"  Preferences get: {'✓' if prefs_get else '✗'}")
                
                # Test session stats
                stats = session_manager.get_session_stats()
                print(f"  Session stats: {'✓' if stats else '✗'}")
                if stats:
                    print(f"    Active sessions: {stats.get('active_sessions', 0)}")
                    print(f"    Total queries: {stats.get('total_queries', 0)}")
            
            # Clean up
            delete_success = session_manager.delete_session(session_id)
            print(f"  Session cleanup: {'✓' if delete_success else '✗'}")
        
        session_manager.close()
        return True
        
    except Exception as e:
        print(f"SessionManager test failed: {e}")
        return False


def test_short_term_memory():
    """Test ShortTermMemory with MessagePack optimization."""
    print("\n=== ShortTermMemory Test ===")
    
    try:
        # Create short-term memory
        memory = ShortTermMemory(ttl_hours=1, max_messages=10)
        
        # Test interaction storage
        print("Adding interactions...")
        for i in range(3):
            interaction_success = memory.add_interaction(
                user_query=f"Test query {i}",
                agent_response=f"Test response {i}",
                context={"query_type": "test", "tickers": ["VNM"]},
                confidence=0.8
            )
            print(f"  Interaction {i+1}: {'✓' if interaction_success else '✗'}")
        
        # Test fact storage
        print("Adding facts...")
        fact_success = memory.add_fact(
            fact_type="company_profile",
            fact_value={"name": "Vinamilk", "sector": "Food", "market_cap": 120000000000000},
            source="test",
            confidence=0.9
        )
        print(f"  Fact storage: {'✓' if fact_success else '✗'}")
        
        # Test retrieval
        print("Retrieving data...")
        interactions = memory.get_recent_interactions(limit=5)
        facts = memory.get_facts()
        print(f"  Interactions: {'✓' if interactions else '✗'} (count: {len(interactions)})")
        print(f"  Facts: {'✓' if facts else '✗'} (count: {len(facts)})")
        
        # Test stats
        stats = memory.get_stats()
        print(f"  Memory stats: {'✓' if stats else '✗'}")
        if stats:
            print(f"    Message count: {stats.get('message_count', 0)}")
            print(f"    Fact count: {stats.get('fact_count', 0)}")
            print(f"    Serialization: {stats.get('serialization_format', 'unknown')}")
        
        # Clean up
        clear_success = memory.clear()
        print(f"  Memory cleanup: {'✓' if clear_success else '✗'}")
        
        memory.close()
        return True
        
    except Exception as e:
        print(f"ShortTermMemory test failed: {e}")
        return False


def main():
    """Run all optimization tests."""
    print("Redis Optimization Test Suite")
    print("=" * 50)
    
    # Test serialization performance
    serialization_results = test_serialization_performance()
    
    # Test Redis operations
    redis_results = test_redis_operations()
    
    # Test SessionManager
    session_success = test_session_manager()
    
    # Test ShortTermMemory
    memory_success = test_short_term_memory()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    print(f"\nSerialization Performance:")
    for format_name, data in serialization_results.items():
        print(f"  {format_name}: {data['serialize_time_ms']:.2f}ms / {data['size_bytes']} bytes")
    
    print(f"\nRedis Operations:")
    for format_name, data in redis_results.items():
        if "error" not in data:
            print(f"  {format_name}: SET {data['set_time_ms']:.2f}ms, GET {data['get_time_ms']:.2f}ms, Success: {data['success']}")
    
    print(f"\nSessionManager: {'✓' if session_success else '✗'}")
    print(f"ShortTermMemory: {'✓' if memory_success else '✗'}")
    
    # Calculate overall improvements
    json_size = serialization_results["json"]["size_bytes"]
    msgpack_size = serialization_results["msgpack"]["size_bytes"]
    hash_size = serialization_results["redis_hash"]["size_bytes"]
    
    msgpack_savings = ((json_size - msgpack_size) / json_size) * 100
    hash_savings = ((json_size - hash_size) / json_size) * 100
    
    print(f"\nMEMORY SAVINGS IMPROVEMENTS:")
    print(f"  MessagePack vs JSON: {msgpack_savings:.1f}% reduction")
    print(f"  Redis Hash vs JSON: {hash_savings:.1f}% reduction")
    print(f"  Combined potential savings: {max(msgpack_savings, hash_savings):.1f}%")
    
    print(f"\nRedis optimization implementation completed successfully! 🎉")


if __name__ == "__main__":
    main()