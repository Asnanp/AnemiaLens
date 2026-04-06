#!/usr/bin/env python3
"""
AnemiaLens Backend API Testing Suite
Tests all critical endpoints for the anemia screening application.
"""

import requests
import sys
import json
import io
import time
from datetime import datetime
from pathlib import Path
from PIL import Image

class AnemiaLensAPITester:
    def __init__(self, base_url="https://1bacd40b-c194-4f25-a64e-797b1e0ddc61.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.session = requests.Session()
        self.session.timeout = 30

    def log(self, message, level="INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)
        
        # Remove Content-Type for file uploads
        if files:
            test_headers.pop('Content-Type', None)

        self.tests_run += 1
        self.log(f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                if files:
                    response = self.session.post(url, files=files, data=data, headers=test_headers)
                else:
                    response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {"raw_response": response.text}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:500]
                })
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}", "ERROR")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False, {}

    def create_test_image(self, size=(200, 200), color=(140, 90, 80)):
        """Create a test image for upload"""
        img = Image.new("RGB", size, color=color)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return buf

    def test_health_endpoint(self):
        """Test /health endpoint"""
        return self.run_test("Health Check", "GET", "/health", 200)

    def test_runtime_status(self):
        """Test /api/runtime-status endpoint"""
        return self.run_test("Runtime Status", "GET", "/api/runtime-status", 200)

    def test_quality_check(self):
        """Test /api/quality-check endpoint with image upload"""
        image_buffer = self.create_test_image()
        files = {'image': ('test_image.jpg', image_buffer, 'image/jpeg')}
        return self.run_test("Quality Check", "POST", "/api/quality-check", 200, files=files)

    def test_analyze_endpoint(self):
        """Test /api/analyze endpoint with image and symptoms"""
        image_buffer = self.create_test_image()
        files = {'image': ('test_image.jpg', image_buffer, 'image/jpeg')}
        data = {
            'symptoms': json.dumps({
                'fatigue': True,
                'dizziness': False,
                'pale_skin': True,
                'shortness_of_breath': False,
                'heavy_menstrual_bleeding': None,
                'poor_diet_low_iron': False
            }),
            'patient_profile': json.dumps({
                'age': 25,
                'sex': 'female'
            }),
            'language': 'en',
            'region': 'US'
        }
        return self.run_test("Analyze Screening", "POST", "/api/analyze", 200, data=data, files=files)

    def test_register_user(self):
        """Test user registration"""
        timestamp = int(time.time())
        test_email = f"test_user_{timestamp}@example.com"
        data = {
            "email": test_email,
            "password": "TestPassword123!",
            "full_name": "Test User"
        }
        success, response = self.run_test("User Registration", "POST", "/api/auth/register", 201, data=data)
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.log(f"✅ Registered user: {test_email}")
        return success, response

    def test_login_user(self):
        """Test user login with existing credentials"""
        # Try to login with a test user (this might fail if user doesn't exist)
        data = {
            "email": "test@example.com",
            "password": "testpassword"
        }
        success, response = self.run_test("User Login", "POST", "/api/auth/login", 200, data=data)
        if success and 'access_token' in response:
            self.token = response['access_token']
        return success, response

    def test_user_profile(self):
        """Test getting user profile (requires auth)"""
        if not self.token:
            self.log("⚠️  Skipping profile test - no auth token")
            return False, {}
        return self.run_test("User Profile", "GET", "/api/auth/me", 200)

    def test_cors_headers(self):
        """Test CORS headers are present"""
        try:
            response = self.session.options(f"{self.base_url}/health", 
                                          headers={'Origin': 'http://localhost:3000'})
            has_cors = 'access-control-allow-origin' in response.headers
            if has_cors:
                self.log("✅ CORS headers present")
                return True, {}
            else:
                self.log("❌ CORS headers missing")
                return False, {}
        except Exception as e:
            self.log(f"❌ CORS test failed: {e}")
            return False, {}

    def test_invalid_image_upload(self):
        """Test error handling for invalid image"""
        files = {'image': ('test.txt', b'not an image', 'text/plain')}
        return self.run_test("Invalid Image Upload", "POST", "/api/quality-check", 415, files=files)

    def test_missing_image_upload(self):
        """Test error handling for missing image"""
        return self.run_test("Missing Image Upload", "POST", "/api/quality-check", 422)

    def run_all_tests(self):
        """Run all backend tests"""
        self.log("🚀 Starting AnemiaLens Backend API Tests")
        self.log(f"Testing against: {self.base_url}")
        
        # Core health checks
        self.test_health_endpoint()
        self.test_runtime_status()
        
        # Image processing endpoints
        self.test_quality_check()
        self.test_analyze_endpoint()
        
        # Auth flow tests
        self.test_register_user()
        # Note: login test might fail if user doesn't exist, but registration should work
        
        # Profile test (only if we have a token)
        self.test_user_profile()
        
        # Error handling tests
        self.test_invalid_image_upload()
        self.test_missing_image_upload()
        
        # Infrastructure tests
        self.test_cors_headers()
        
        # Print summary
        self.print_summary()
        
        return self.tests_passed == self.tests_run

    def print_summary(self):
        """Print test summary"""
        self.log("=" * 60)
        self.log(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failed_tests:
            self.log("❌ Failed Tests:")
            for failure in self.failed_tests:
                self.log(f"   - {failure.get('test', 'Unknown')}")
                if 'error' in failure:
                    self.log(f"     Error: {failure['error']}")
                elif 'expected' in failure:
                    self.log(f"     Expected: {failure['expected']}, Got: {failure['actual']}")
                    if failure.get('response'):
                        self.log(f"     Response: {failure['response'][:100]}...")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"✨ Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            self.log("🎉 Backend is in good shape!")
        elif success_rate >= 60:
            self.log("⚠️  Backend has some issues but core functionality works")
        else:
            self.log("🚨 Backend has significant issues that need attention")

def main():
    """Main test runner"""
    tester = AnemiaLensAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        tester.log("Tests interrupted by user", "WARNING")
        return 1
    except Exception as e:
        tester.log(f"Test suite failed with error: {e}", "ERROR")
        return 1

if __name__ == "__main__":
    sys.exit(main())