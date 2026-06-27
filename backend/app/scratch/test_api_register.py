import json
import urllib.request
import urllib.error

def test_api_register():
    url = "http://localhost:8000/api/v1/auth/register"
    data = {
        "name": "api_test",
        "email": "vishnu_test@gmail.com",
        "password": "password123",
        "role": "Employee"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Status Code: {resp.status}")
            print(f"Response: {resp.read().decode('utf-8')}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code}")
        print(f"Response: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error connecting to backend: {str(e)}")

if __name__ == "__main__":
    test_api_register()
