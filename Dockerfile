# ใช้ Python เวอร์ชันเล็กกะทัดรัด (Slim)
FROM python:3.10-slim

# ตั้งโฟลเดอร์ทำงานข้างใน Container
WORKDIR /app

# ก็อปปี้ไฟล์ requirements ไปก่อน (เพื่อ Cache layer การ install)
COPY requirements.txt .

# ติดตั้ง Library
RUN pip install --no-cache-dir -r requirements.txt

# ก็อปปี้โค้ดทั้งหมดเข้าไป
COPY . .

# คำสั่งรันบอทเมื่อ Container เริ่มทำงาน
CMD ["python", "main.py"]