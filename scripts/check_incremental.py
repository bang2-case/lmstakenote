"""
Kiểm tra API có hỗ trợ filter updatedAt/createdAt_gte không.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests, json
from main import GRAPHQL_URL, HEADERS

# Introspect ClassFilter input để tìm các filter có sẵn
payload = {
    "query": """
    {
      __type(name: "ClassFilter") {
        inputFields { name type { name kind ofType { name } } }
      }
    }
    """
}
res = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=10)
data = res.json()
t = (data.get("data") or {}).get("__type") or {}
fields = t.get("inputFields") or []

print("=== ClassFilter fields ===")
for f in fields:
    name = f.get("name", "")
    if any(k in name.lower() for k in ["date", "update", "create", "time"]):
        print(f"  DATE: {name}")
    else:
        print(f"       {name}")
