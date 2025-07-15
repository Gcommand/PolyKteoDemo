#!/usr/bin/env python3
"""
Security test script to verify the security improvements in app.py.
This script tests various attack vectors that should now be blocked.
"""

import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_CASES = [
    {
        "name": "SQL Injection in tech_sector_id",
        "url": f"{BASE_URL}/search?query=test&tech_sector_id=1';DROP TABLE patents;--",
        "expected_status": 400,
        "description": "Tests SQL injection prevention in tech_sector_id parameter"
    },
    {
        "name": "JavaScript Injection in tech_sector_id",
        "url": f"{BASE_URL}/search?query=test&tech_sector_id=2;var%20fs=require('fs');if(fs!=null)console.log('hacked');",
        "expected_status": 400,
        "description": "Tests JavaScript injection prevention (original vulnerability)"
    },
    {
        "name": "XSS in query parameter",
        "url": f"{BASE_URL}/search?query=<script>alert('xss')</script>&confidence_level=0.2",
        "expected_status": 400,
        "description": "Tests XSS prevention in query parameter"
    },
    {
        "name": "Null byte injection",
        "url": f"{BASE_URL}/search?query=test\x00malicious&department=1",
        "expected_status": 400,
        "description": "Tests null byte injection prevention"
    },
    {
        "name": "Invalid confidence level",
        "url": f"{BASE_URL}/search?query=test&confidence_level=1.5",
        "expected_status": 400,
        "description": "Tests parameter range validation"
    },
    {
        "name": "Invalid sorting order",
        "url": f"{BASE_URL}/search?query=test&sorting_order=INVALID_ORDER",
        "expected_status": 400,
        "description": "Tests sorting order validation"
    },
    {
        "name": "Non-numeric department ID",
        "url": f"{BASE_URL}/search?query=test&department=abc",
        "expected_status": 400,
        "description": "Tests numeric parameter validation"
    },
    {
        "name": "LDAP Injection in current_page (original vulnerability)",
        "url": f"{BASE_URL}/search?query=test&current_page=*)(!%20cn=*1226805346void)",
        "expected_status": 400,
        "description": "Tests LDAP injection prevention in current_page parameter (reported vulnerability)"
    },
    {
        "name": "LDAP Injection with uid attribute",
        "url": f"{BASE_URL}/search?query=test&page_size=1)(uid=*",
        "expected_status": 400,
        "description": "Tests LDAP injection prevention with uid attribute"
    },
    {
        "name": "LDAP Injection with objectClass",
        "url": f"{BASE_URL}/search?query=test&department=1)(objectClass=*",
        "expected_status": 400,
        "description": "Tests LDAP injection prevention with objectClass attribute"
    },
    {
        "name": "LDAP OR operator injection",
        "url": f"{BASE_URL}/search?query=test||malicious&confidence_level=0.2",
        "expected_status": 400,
        "description": "Tests LDAP OR operator injection prevention"
    },
    {
        "name": "Valid request",
        "url": f"{BASE_URL}/search?query=test&confidence_level=0.2&department=1",
        "expected_status": 200,
        "description": "Tests that valid requests still work"
    }
]

def test_security_improvements():
    """Run security tests and report results."""
    print("=== SECURITY TEST RESULTS ===\n")
    
    passed_tests = 0
    total_tests = len(TEST_CASES)
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"Test {i}/{total_tests}: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        
        try:
            # Make request with suspicious User-Agent to test detection
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; security-test)'
            }
            
            response = requests.get(test_case['url'], headers=headers, timeout=10)
            
            if response.status_code == test_case['expected_status']:
                print(f"✅ PASSED - Status: {response.status_code}")
                passed_tests += 1
            else:
                print(f"❌ FAILED - Expected: {test_case['expected_status']}, Got: {response.status_code}")
                print(f"   Response: {response.text[:100]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR - Request failed: {str(e)}")
        
        print("-" * 50)
    
    print(f"\nSUMMARY: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL SECURITY TESTS PASSED! The application is now secure.")
    else:
        print("⚠️  Some tests failed. Please review the security implementation.")

def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\n=== RATE LIMITING TEST ===\n")
    
    # Make multiple requests quickly to test rate limiting
    print("Sending 5 requests quickly to test rate limiting...")
    
    for i in range(5):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            print(f"Request {i+1}: Status {response.status_code}")
            if response.status_code == 429:
                print("✅ Rate limiting is working!")
                break
        except requests.exceptions.RequestException as e:
            print(f"Request {i+1}: Error - {str(e)}")
        
        time.sleep(0.1)  # Small delay between requests

def test_security_headers():
    """Test security headers."""
    print("\n=== SECURITY HEADERS TEST ===\n")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Content-Security-Policy'
        ]
        
        for header in security_headers:
            if header in response.headers:
                print(f"✅ {header}: {response.headers[header]}")
            else:
                print(f"❌ {header}: Missing")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR - Request failed: {str(e)}")

if __name__ == "__main__":
    print("Starting security tests for the PolyU Patent Search API...")
    print("Make sure the Flask application is running on http://localhost:5000\n")
    
    test_security_improvements()
    test_rate_limiting()
    test_security_headers()
    
    print("\n=== ADDITIONAL SECURITY RECOMMENDATIONS ===")
    print("1. Enable HTTPS in production")
    print("2. Use a proper authentication system (JWT, OAuth)")
    print("3. Implement database connection pooling")
    print("4. Add request logging to a secure location")
    print("5. Use environment variables for sensitive configuration")
    print("6. Implement proper CORS policy")
    print("7. Add input sanitization for database queries")
    print("8. Use a WAF (Web Application Firewall) in production") 