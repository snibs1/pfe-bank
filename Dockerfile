# 1. جيب لينا بايثون واجد
FROM python:3.9-slim

# 2. تسطال ملفات السيستيم الضرورية لـ LightGBM و Postgres
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 3. صاوب الدوسي وسط الكونطونير
WORKDIR /app

# 4. كوبي ملف التقضية وسطال المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. كوبي الكود والموديلات كاملين
COPY . .

# 6. حل الباب رقم 5000
EXPOSE 5000

# 7. تشغيل السيت
ENV FLASK_APP=app.py
CMD ["flask", "run", "--host=0.0.0.0"]