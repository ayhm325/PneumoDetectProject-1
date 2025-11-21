import requests

# اختبار نقطة /api/analyze بصورة حقيقية
url = "http://127.0.0.1:5000/api/analyze"
image_path = "app/static/assets/images/placeholder-xray.svg"  # استخدم صورة موجودة فعلياً

with open(image_path, "rb") as img:
    files = {"file": (image_path, img, "image/svg+xml")}
    response = requests.post(url, files=files)
    print("/api/analyze status:", response.status_code)
    print(response.json())

# اختبار نقطة /api/analyze بملف غير صورة
with open("app/static/core.js", "rb") as f:
    files = {"file": ("core.js", f, "application/javascript")}
    response = requests.post(url, files=files)
    print("/api/analyze (not image) status:", response.status_code)
    print(response.json())
