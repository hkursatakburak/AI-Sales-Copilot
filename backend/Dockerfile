# ── Aşama 1: Bağımlılıkları yükle ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Sistem paketleri (Playwright için gerekli)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Playwright Chromium tarayıcısını indir
ENV PLAYWRIGHT_BROWSERS_PATH=/install/playwright
RUN pip install --no-cache-dir playwright && \
    python -m playwright install chromium --with-deps

# ── Aşama 2: Çalışma zamanı ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Playwright'ın ihtiyaç duyduğu sistem kütüphaneleri
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Yüklü Python paketlerini builder'dan kopyala
COPY --from=builder /install /usr/local
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/local/playwright

# Uygulama kullanıcısı (root olarak çalışma)
RUN useradd --no-create-home --shell /bin/false appuser

WORKDIR /app
COPY app/ ./app/

# SQLite DB dizini — volume ile dışarıdan bağlanabilir
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
