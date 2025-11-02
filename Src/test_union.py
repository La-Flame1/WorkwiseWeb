import requests
from typing import Any

url = "http://localhost:8000/v1/workwise/unions"
headers = {"Content-Type": "application/json", "X-Endpoint-Token": "UNIONCREATETOK789"}
data: dict[str, Any] = {
    "register_num": "REG-2025-008",
    "sector_info": "Education",
    "membership_size": 12,
    "is_active_council": False
}

response = requests.post(url, json=data, headers=headers)
print(f"Status: {response.status_code}")
print(f"Body: {response.json() if response.ok else response.text}")