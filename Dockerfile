FROM python:3.11-slim

# ضبط متغيرات بايثون لتفادي التخزين المؤقت للبيانات النصية
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# تثبيت متطلبات النظام الأساسية لمكتبات التحليل والـ PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# تثبيت حزم بايثون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كود المشروع بالكامل
COPY . .

# فحص صحة تشغيل الحاوية (Healthcheck)
HEALTHCHECK CMD curl --fail http://localhost:${PORT}/_stcore/health || exit 1

# تشغيل Streamlit بتهيئة الإنتاجية لمنع القيود الشبكية
ENTRYPOINT ["sh", "-c", "streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false"]
