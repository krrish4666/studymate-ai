import json, uuid, http.client

BASE = "http://127.0.0.1:8000/api/v1"

def multipart_post(path, fields, file_field, file_name, file_data, token):
    boundary = str(uuid.uuid4())
    body = b""
    for key, value in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="{file_field}"; filename="{file_name}"\r\n'.encode()
    body += "Content-Type: text/plain\r\n\r\n".encode()
    body += file_data + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    conn = http.client.HTTPConnection("127.0.0.1", 8000)
    conn.request("POST", path, body=body, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    r = conn.getresponse()
    resp_data = r.read().decode()
    return resp_data, r.status

# 1. Login
data = json.dumps({"email": "test@test.com", "password": "test1234"}).encode()
conn = http.client.HTTPConnection("127.0.0.1", 8000)
conn.request("POST", f"{BASE}/auth/login", data, {"Content-Type": "application/json"})
r = conn.getresponse()
body = json.loads(r.read())
token = body["access_token"]
print(f"1. Logged in: {body['user']['email']}")

# 2. Upload
result, status = multipart_post(
    f"{BASE}/upload",
    {"feature": "notes"},
    "file", "test.txt",
    b"Photosynthesis is the process by which plants convert sunlight into chemical energy.",
    token
)
print(f"2. Upload status={status}, response={result[:200]}")

if status == 200:
    data = json.loads(result)
    file_id = data["fileRecordId"]
    print(f"   fileId={file_id}")

    # 3. Notes
    conn = http.client.HTTPConnection("127.0.0.1", 8000)
    conn.request("POST", f"{BASE}/features/notes",
        json.dumps({"fileRecordId": file_id, "mode": "detailed"}).encode(),
        {"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    r = conn.getresponse()
    print(f"3. Notes status: {r.status}")
    raw = r.read().decode()
    print(f"   Response: {raw[:500]}")
