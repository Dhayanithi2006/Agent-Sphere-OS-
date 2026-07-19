import requests
import json
import time

def run_test():
    url = "http://127.0.0.1:8000/kernel/execute"
    payload = {
        "task": "Create a short AI movie about a robot.",
        "workflow": "showrunner"
    }
    
    print(f"Sending POST to {url}...")
    start = time.time()
    try:
        response = requests.post(url, json=payload, timeout=120)
        end = time.time()
        print(f"Status Code: {response.status_code}")
        print(f"Time Taken: {end - start:.2f}s")
        
        try:
            data = response.json()
            print("Response JSON:")
            print(json.dumps(data, indent=2))
        except Exception:
            print("Response text:")
            print(response.text)
    except Exception as e:
        print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    run_test()
