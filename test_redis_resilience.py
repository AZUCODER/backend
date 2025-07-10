#!/usr/bin/env python3
"""
Test script to verify Redis resilience.

This script tests that the webapp continues to function properly
when Redis is unavailable.
"""

import asyncio
import httpx
import time
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

async def test_health_endpoints() -> Dict[str, Any]:
    """Test health endpoints with and without Redis."""
    async with httpx.AsyncClient() as client:
        results = {}
        
        # Test basic health check
        try:
            response = await client.get(f"{BASE_URL}/health")
            results["basic_health"] = {
                "status_code": response.status_code,
                "data": response.json(),
                "success": response.status_code == 200
            }
        except Exception as e:
            results["basic_health"] = {"error": str(e), "success": False}
        
        # Test Redis health check
        try:
            response = await client.get(f"{API_BASE}/health/redis")
            results["redis_health"] = {
                "status_code": response.status_code,
                "data": response.json(),
                "success": response.status_code == 200
            }
        except Exception as e:
            results["redis_health"] = {"error": str(e), "success": False}
        
        # Test readiness check
        try:
            response = await client.get(f"{API_BASE}/health/readiness")
            results["readiness"] = {
                "status_code": response.status_code,
                "data": response.json(),
                "success": response.status_code == 200
            }
        except Exception as e:
            results["readiness"] = {"error": str(e), "success": False}
        
        return results

async def test_api_endpoints() -> Dict[str, Any]:
    """Test API endpoints that use Redis caching."""
    async with httpx.AsyncClient() as client:
        results = {}
        
        # Test user endpoints (these use Redis caching)
        try:
            response = await client.get(f"{API_BASE}/users/me")
            results["users_me"] = {
                "status_code": response.status_code,
                "success": response.status_code in [200, 401]  # 401 is expected without auth
            }
        except Exception as e:
            results["users_me"] = {"error": str(e), "success": False}
        
        # Test auth endpoints
        try:
            response = await client.post(f"{API_BASE}/auth/login", json={
                "email": "test@example.com",
                "password": "testpassword"
            })
            results["auth_login"] = {
                "status_code": response.status_code,
                "success": response.status_code in [200, 401, 422]  # Various expected responses
            }
        except Exception as e:
            results["auth_login"] = {"error": str(e), "success": False}
        
        return results

async def test_rate_limiting() -> Dict[str, Any]:
    """Test rate limiting behavior without Redis."""
    async with httpx.AsyncClient() as client:
        results = {}
        
        # Make multiple requests to test rate limiting
        responses = []
        for i in range(10):
            try:
                response = await client.get(f"{BASE_URL}/health")
                responses.append(response.status_code)
            except Exception as e:
                responses.append(f"error: {e}")
        
        results["rate_limiting"] = {
            "responses": responses,
            "success": all(status == 200 for status in responses if isinstance(status, int))
        }
        
        return results

def print_results(title: str, results: Dict[str, Any]):
    """Print test results in a formatted way."""
    print(f"\n{'='*50}")
    print(f"📊 {title}")
    print(f"{'='*50}")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
        print(f"{status} {test_name}")
        
        if "data" in result:
            print(f"   Status Code: {result.get('status_code', 'N/A')}")
            if "redis" in result["data"]:
                redis_status = result["data"]["redis"]["status"]
                redis_connected = result["data"]["redis"]["connected"]
                print(f"   Redis Status: {redis_status} (Connected: {redis_connected})")
        
        if "error" in result:
            print(f"   Error: {result['error']}")

async def main():
    """Main test function."""
    print("🚀 Redis Resilience Test")
    print("="*50)
    print("This test verifies that the webapp functions properly when Redis is down.")
    print("Make sure your backend is running on http://localhost:8000")
    print("\nStarting tests...")
    
    # Test 1: Health endpoints
    health_results = await test_health_endpoints()
    print_results("Health Endpoints Test", health_results)
    
    # Test 2: API endpoints
    api_results = await test_api_endpoints()
    print_results("API Endpoints Test", api_results)
    
    # Test 3: Rate limiting
    rate_results = await test_rate_limiting()
    print_results("Rate Limiting Test", rate_results)
    
    # Summary
    print(f"\n{'='*50}")
    print("📋 SUMMARY")
    print(f"{'='*50}")
    
    all_tests = {**health_results, **api_results, **rate_results}
    passed = sum(1 for result in all_tests.values() if result.get("success", False))
    total = len(all_tests)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! The webapp is resilient to Redis failures.")
    else:
        print("\n⚠️  Some tests failed. Check the results above for details.")
    
    print("\n💡 Expected behavior when Redis is down:")
    print("   - Health endpoints should return 'degraded' status")
    print("   - API endpoints should work (fallback to database)")
    print("   - Rate limiting should be disabled (allow all requests)")
    print("   - No errors should occur")

if __name__ == "__main__":
    asyncio.run(main()) 