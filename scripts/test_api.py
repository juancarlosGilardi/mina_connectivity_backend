#!/usr/bin/env python3
"""
Script para probar la API Mina Connectivity Test
"""
import requests
import json
import time
import uuid
from typing import Dict, Any

class MinaAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        
    def test_health(self) -> bool:
        """Test health check"""
        print("🔍 Testing health check...")
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health: {data['status']}, DB: {data['database']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_metrics(self) -> bool:
        """Test metrics endpoint"""
        print("📊 Testing metrics...")
        try:
            response = requests.get(f"{self.api_url}/metrics", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Metrics: {data.get('total_requests', 0)} total requests")
                return True
            else:
                print(f"❌ Metrics failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Metrics error: {e}")
            return False
    
    def test_standard_payload(self) -> bool:
        """Test 1: Payload estándar"""
        print("1️⃣  Testing standard payload...")
        payload = {
            "userName": "Test User",
            "userEmail": "test@mina.com",
            "userDni": "12345678",
            "qrCode": f"QR_{int(time.time())}",
            "marcationType": "Ingreso",
            "latitude": -12.0464,
            "longitude": -77.0428,
            "deviceId": "test_device_001"
        }
        
        try:
            response = requests.post(f"{self.api_url}/test/1-standard", 
                                   json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Standard: {data['payload_size_bytes']} bytes, "
                      f"{data['processing_time_ms']}ms")
                return True
            else:
                print(f"❌ Standard payload failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Standard payload error: {e}")
            return False
    
    def test_compressed_payload(self) -> bool:
        """Test 2: Payload comprimido"""
        print("2️⃣  Testing compressed payload...")
        payload = {
            "u": "Test User",
            "e": "test@mina.com", 
            "d": "12345678",
            "q": f"QR_{int(time.time())}",
            "t": "Ingreso",
            "lat": -12.0464,
            "lon": -77.0428,
            "dev": "test_device_001"
        }
        
        try:
            response = requests.post(f"{self.api_url}/test/2-compressed", 
                                   json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Compressed: {data['compressed_size_bytes']} bytes, "
                      f"{data['savings_percent']}% saved")
                return True
            else:
                print(f"❌ Compressed payload failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Compressed payload error: {e}")
            return False
    
    def test_idempotent_request(self) -> bool:
        """Test 3: Request idempotente"""
        print("3️⃣  Testing idempotent request...")
        token = str(uuid.uuid4())
        payload = {
            "token_idempotencia": token,
            "data": {
                "userName": "Test User",
                "userEmail": "test@mina.com",
                "userDni": "12345678",
                "qrCode": f"QR_{int(time.time())}",
                "marcationType": "Ingreso",
                "latitude": -12.0464,
                "longitude": -77.0428,
                "deviceId": "test_device_001"
            }
        }
        
        try:
            # Primera llamada
            response1 = requests.post(f"{self.api_url}/test/3-idempotent", 
                                    json=payload, timeout=15)
            
            # Segunda llamada (debería ser duplicada)
            response2 = requests.post(f"{self.api_url}/test/3-idempotent", 
                                    json=payload, timeout=15)
            
            if response1.status_code == 200 and response2.status_code == 200:
                data1 = response1.json()
                data2 = response2.json()
                print(f"✅ Idempotent: First={not data1.get('is_duplicate', False)}, "
                      f"Second={data2.get('is_duplicate', False)}")
                return True
            else:
                print(f"❌ Idempotent failed: {response1.status_code}, {response2.status_code}")
                return False
        except Exception as e:
            print(f"❌ Idempotent error: {e}")
            return False
    
    def run_basic_tests(self):
        """Ejecutar tests básicos"""
        print("=" * 60)
        print("🧪 TESTING MINA CONNECTIVITY API - TESTS BÁSICOS")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health),
            ("Metrics", self.test_metrics),
            ("Standard Payload", self.test_standard_payload),
            ("Compressed Payload", self.test_compressed_payload),
            ("Idempotent Request", self.test_idempotent_request),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}")
            print()
        
        print("=" * 60)
        print(f"📊 RESULTS: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! API is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the API configuration.")
        
        return passed == total

def main():
    print("🧪 TESTING MINA CONNECTIVITY API")
    print("Asegúrate de que la API esté corriendo en http://localhost:8000")
    print()
    
    tester = MinaAPITester()
    success = tester.run_basic_tests()
    
    if success:
        print("\n🎉 ¡Todos los tests pasaron! La API está funcionando correctamente.")
    else:
        print("\n⚠️  Algunos tests fallaron. Revisa la configuración.")

if __name__ == "__main__":
    main()
