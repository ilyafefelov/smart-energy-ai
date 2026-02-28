"""
Quick test to verify ML API endpoint works via curl
"""
import subprocess
import json
import time

def test_api_endpoint():
    """Test the ML API endpoint using curl."""
    print("🧪 Testing ML API Endpoint...")
    
    # Wait a moment for server to be ready
    print("⏳ Waiting for server startup...")
    time.sleep(3)
    
    try:
        # Test the ML recommendation endpoint
        result = subprocess.run([
            'curl', '-s', 
            'http://localhost:3000/api/ml/recommendation'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ Curl failed: {result.stderr}")
            return False
            
        try:
            response_data = json.loads(result.stdout)
            print(f"✅ API Response received: {json.dumps(response_data, indent=2)}")
            
            if response_data.get('success'):
                print("✅ API endpoint working correctly!")
                return True
            else:
                print(f"⚠️ API returned error: {response_data.get('error', 'Unknown error')}")
                return False
                
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Request timed out - server may not be running")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_api_endpoint()
    exit(0 if success else 1)