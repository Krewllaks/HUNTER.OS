# 1. Playwright için özel hazırlanmış resmi imajı kullanıyoruz. 
# İçinde Python 3.12 ve tüm tarayıcı bağımlılıkları (fontlar dahil) hazır gelir.
FROM mcr.microsoft.com/playwright/python:v1.49.1-noble AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/app/.playwright

WORKDIR /app

# Gerekli sistem paketlerini ekle (curl healthcheck için lazım)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright tarayıcı klasörünü hazırla
RUN mkdir -p /app/.playwright

# Tarayıcıyı indir. '--with-deps' eklemene gerek yok, 
# çünkü Microsoft'un bu imajında tüm bağımlılıklar zaten yüklü.
RUN playwright install chromium

# Uygulama kodlarını kopyala
COPY . .

# Entrypoint yetkisini ver ve hazırla
RUN chmod +x /app/scripts/entrypoint.sh

EXPOSE 8000

# Senin eklediğin harika healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Migration'ları yap ve uygulamayı başlat.
# CMD shell-form kullanıyoruz ki ${PORT:-8000} Railway tarafından
# atanan dinamik port env-var'ını expand etsin.
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}