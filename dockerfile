FROM python:3.11-slim

# جلوگیری از لاگ‌های اضافی
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# نصب ffmpeg و وابستگی‌ها
RUN apt-get update \
    && apt-get install -y ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# پوشه دانلود
RUN mkdir -p downloads

# پورت Render
EXPOSE 10000

CMD ["python", "main.py"]
