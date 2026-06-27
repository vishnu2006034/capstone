import sys
import time
import subprocess
import urllib.request
import urllib.error
import json

def debug():
    print("Starting uvicorn server on port 12345...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.app:app", "--port", "12345"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to spin up
    time.sleep(3.0)
    
    url = "http://localhost:12345/api/v1/auth/register"
    data = {
        "name": "debug_user",
        "email": "debug@company.com",
        "password": "password123",
        "role": "Employee"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    response_received = None
    try:
        with urllib.request.urlopen(req) as resp:
            response_received = f"Success! Status: {resp.status}, Body: {resp.read().decode('utf-8')}"
    except urllib.error.HTTPError as e:
        response_received = f"HTTP Error {e.code}: {e.read().decode('utf-8')}"
    except Exception as e:
        response_received = f"Connection error: {str(e)}"
        
    # Terminate server
    proc.terminate()
    try:
        stdout, stderr = proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        
    print("\n=== CLIENT RESPONSE ===")
    print(response_received)
    print("\n=== SERVER STDOUT ===")
    print(stdout)
    print("\n=== SERVER STDERR ===")
    print(stderr)

if __name__ == "__main__":
    debug()
