import json, urllib.request

token = "8822383019:AAFkgbR-Hs-6HrvBpVnjohZyqPEir4OjRlk"
url = f"https://api.telegram.org/bot{token}/getUpdates"
data = json.loads(urllib.request.urlopen(url).read())
for m in data.get("result", []):
    if "message" in m:
        f = m["message"]["from"]
        print(f"ID: {f['id']} - @{f.get('username', '?')}")
