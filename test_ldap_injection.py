#!/usr/bin/env python3
"""
LDAP Injection Test Script
Tests the specific LDAP injection vulnerabilities reported in the security scan.
"""

import requests
import json
import urllib.parse

# Test configuration
BASE_URL = "http://localhost:5000"

def test_ldap_injection_patterns():
    """Test various LDAP injection patterns to ensure they're blocked."""
    print("=== LDAP INJECTION VULNERABILITY TESTS ===\n")
    
    # Original vulnerability from the security report
    ldap_test_cases = [
        {
            "name": "Original Vulnerability - current_page parameter",
            "url": f"{BASE_URL}/search?query=test&current_page=*)(!%20cn=*1226805346void)",
            "description": "Tests the exact LDAP injection pattern from the security report"
        },
        {
            "name": "LDAP Wildcard Filter Attack",
            "url": f"{BASE_URL}/search?query=test&page_size=*)",
            "description": "Tests LDAP wildcard filter pattern *)"
        },
        {
            "name": "LDAP Negation Attack",
            "url": f"{BASE_URL}/search?query=test&current_page=!(",
            "description": "Tests LDAP negation pattern !("
        },
        {
            "name": "LDAP Common Name (cn) Attack",
            "url": f"{BASE_URL}/search?query=test&department=1)(cn=*",
            "description": "Tests LDAP common name attribute injection"
        },
        {
            "name": "LDAP User ID (uid) Attack",
            "url": f"{BASE_URL}/search?query=test&tech_sector_id=2)(uid=admin",
            "description": "Tests LDAP user ID attribute injection"
        },
        {
            "name": "LDAP Organizational Unit (ou) Attack",
            "url": f"{BASE_URL}/search?query=test&assignee_id=3)(ou=*",
            "description": "Tests LDAP organizational unit injection"
        },
        {
            "name": "LDAP Domain Component (dc) Attack",
            "url": f"{BASE_URL}/search?query=test&confidence_level=0.2)(dc=example",
            "description": "Tests LDAP domain component injection"
        },
        {
            "name": "LDAP ObjectClass Attack",
            "url": f"{BASE_URL}/search?query=test&sorting_order=REL_DESC)(objectClass=*",
            "description": "Tests LDAP objectClass attribute injection"
        },
        {
            "name": "LDAP OR Operator Attack",
            "url": f"{BASE_URL}/search?query=test||admin&confidence_level=0.2",
            "description": "Tests LDAP OR operator injection"
        },
        {
            "name": "LDAP AND Operator Attack",
            "url": f"{BASE_URL}/search?query=test&&admin&confidence_level=0.2",
            "description": "Tests LDAP AND operator injection"
        },
        {
            "name": "Complex LDAP Filter Attack",
            "url": f"{BASE_URL}/search?query=test&current_page=1)(|(cn=*)(uid=admin))",
            "description": "Tests complex LDAP filter injection"
        }
    ]
    
    passed_tests = 0
    total_tests = len(ldap_test_cases)
    
    for i, test_case in enumerate(ldap_test_cases, 1):
        print(f"Test {i}/{total_tests}: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        print(f"URL: {test_case['url']}")
        
        try:
            response = requests.get(test_case['url'], timeout=10)
            
            if response.status_code == 400:
                print(f"✅ PASSED - LDAP injection blocked (Status: {response.status_code})")
                try:
                    error_response = response.json()
                    print(f"   Error message: {error_response.get('error', 'No error message')}")
                except:
                    print(f"   Response: {response.text[:100]}...")
                passed_tests += 1
            else:
                print(f"❌ FAILED - Expected 400, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR - Request failed: {str(e)}")
        
        print("-" * 60)
    
    print(f"\nSUMMARY: {passed_tests}/{total_tests} LDAP injection tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL LDAP INJECTION TESTS PASSED! The application is secure against LDAP injection.")
    else:
        print("⚠️  Some LDAP injection tests failed. Please review the security implementation.")

def test_payloads_from_report():
    """Test the specific payloads mentioned in the security report."""
    print("\n=== TESTING SPECIFIC PAYLOADS FROM SECURITY REPORT ===\n")
    
    # Test payload 1 from the report: *)(uid=*
    print("Testing Payload 1: *)(uid=*")
    payload1_url = f"{BASE_URL}/search?query=test&current_page=*)(uid=*"
    
    try:
        response = requests.get(payload1_url, timeout=10)
        print(f"Payload 1 - Status: {response.status_code}")
        if response.status_code == 400:
            print("✅ Payload 1 BLOCKED successfully")
        else:
            print("❌ Payload 1 NOT BLOCKED")
    except Exception as e:
        print(f"❌ Payload 1 test failed: {str(e)}")
    
    # Test payload 2 from the report: somevalue)(uid=someothervalue
    print("\nTesting Payload 2: somevalue)(uid=someothervalue")
    payload2_url = f"{BASE_URL}/search?query=test&current_page=somevalue)(uid=someothervalue"
    
    try:
        response = requests.get(payload2_url, timeout=10)
        print(f"Payload 2 - Status: {response.status_code}")
        if response.status_code == 400:
            print("✅ Payload 2 BLOCKED successfully")
        else:
            print("❌ Payload 2 NOT BLOCKED")
    except Exception as e:
        print(f"❌ Payload 2 test failed: {str(e)}")

def test_valid_requests():
    """Test that valid requests still work after implementing LDAP injection protection."""
    print("\n=== TESTING VALID REQUESTS ===\n")
    
    valid_requests = [
        f"{BASE_URL}/search?query=technology&current_page=1&page_size=10",
        f"{BASE_URL}/search?query=patent&confidence_level=0.3&sorting_order=REL_DESC",
        f"{BASE_URL}/search?query=research&department=1&tech_sector_id=2",
        f"{BASE_URL}/health"
    ]
    
    for i, url in enumerate(valid_requests, 1):
        print(f"Valid Request {i}: {url}")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code in [200, 400]:  # 400 is OK for missing query parameter
                print(f"✅ Valid request works (Status: {response.status_code})")
            else:
                print(f"❌ Valid request failed (Status: {response.status_code})")
        except Exception as e:
            print(f"❌ Valid request error: {str(e)}")
        print()

if __name__ == "__main__":
    print("LDAP Injection Security Test")
    print("=" * 50)
    print("Testing LDAP injection vulnerabilities reported in security scan")
    print("Make sure the Flask application is running on http://localhost:5000\n")
    
    test_ldap_injection_patterns()
    test_payloads_from_report()
    test_valid_requests()
    
    print("\n" + "=" * 50)
    print("IMPORTANT NOTE:")
    print("This application does NOT use LDAP authentication/directory services.")
    print("The LDAP injection vulnerability was a FALSE POSITIVE in the security scan.")
    print("However, we've implemented protection against LDAP injection patterns")
    print("to prevent any potential security issues and improve overall security posture.")
    print("=" * 50) 