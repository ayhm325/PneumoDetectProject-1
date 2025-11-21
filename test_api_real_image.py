import requests

# اختبار نقطة /api/analyze بصورة طبية حقيقية (يفضل صورة jpg/png موجودة فعلياً)
url = "http://127.0.0.1:5000/api/analyze"
image_path = "uploads/originals/00b58889-eebd-47ec-8501-c49417466031.jpg"

with open(image_path, "rb") as img:
    files = {"file": (image_path, img, "image/jpeg")}
    data = {"generate_text_report": "true"}
    response = requests.post(url, files=files, data=data)
    print("/api/analyze (uploads/originals, text report) status:", response.status_code)
    print(response.json())
