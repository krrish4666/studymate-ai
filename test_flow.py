import urllib.request, json, io, uuid, os

BASE = "http://127.0.0.1:8000/api/v1"

# 1. Login
data = json.dumps({"email": "test@test.com", "password": "test1234"}).encode()
req = urllib.request.Request(f"{BASE}/auth/login", data=data, headers={"Content-Type": "application/json"})
r = urllib.request.urlopen(req)
body = json.loads(r.read())
token = body["access_token"]
print("Logged in, token:", token[:30])

# 2. Upload a file
boundary = str(uuid.uuid4())
content = b"Study Notes: Photosynthesis is the process by which plants convert sunlight into energy."
parts = []
parts.append(f"--{boundary}".encode())
parts.append(b'Content-Disposition: form-data; name="file"; filename="test.txt"')
parts.append(b"Content-Type: text/plain")
parts.append(b"")
parts.append(content)
parts.append(f"--{boundary}".encode())
parts.append(b'Content-Disposition: form-data; name="feature"')
parts.append(b"")
parts.append(b"notes")
parts.append(f"--{boundary}--".encode())
body_data = b"\r\n".join(parts)

req = urllib.request.Request(f"{BASE}/upload", data=body_data, headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": f"multipart/form-data; boundary={boundary}",
})
r = urllib.request.urlopen(req)
resp = json.loads(r.read())
print("Upload:", json.dumps(resp, indent=2))

# 3. Try generating notes - this needs an API key
file_id = resp["fileRecordId"]
req = urllib.request.Request(f"{BASE}/features/notes", 
    data=json.dumps({"fileRecordId": file_id, "mode": "detailed"}).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
try:
    r = urllib.request.urlopen(req)
    # Streaming response - read first chunk
    chunk = r.read(500)
    print("Notes response:", chunk.decode()[:300])
except Exception as e:
    print("Notes error:", e)
    if hasattr(e, "read"):
        print("  Body:", e.read().decode()[:300])
