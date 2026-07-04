# AI Sales Copilot

Satış temsilcilerinin işini hızlandıran bir Chrome eklentisi + Python backend.
Bir şirketin web sitesindeyken tek tıkla; **şirket özeti**, **acı noktaları**,
**lead skoru**, **soğuk e-posta** ve **toplantı sunumu** üretir.

> İnsanın 30-45 dakikada yaptığı araştırma + yazma işini ~30 saniyeye indirmeyi hedefler.

## Mimari (özet)

```
Chrome Extension (Manifest V3)
        │  HTTPS / JSON  (POST /analyze)
        ▼
FastAPI Backend  ──►  Scraping (Sprint 2)
   (Clean Arch)  ──►  LLM: Claude (Sprint 3)
                 ──►  Lead Scoring: kural tabanlı (Sprint 3)
                 ──►  Cold Email + Pitch (Sprint 4)
```

Backend **Clean Architecture** ile katmanlıdır; bağımlılıklar hep içeri doğru akar:

| Katman | Sorumluluk | Örnek |
|---|---|---|
| `domain` | Saf iş modelleri + arayüzler (framework'süz) | `CompanyAnalysis`, `AnalysisService` |
| `application` | İş akışı / use-case'ler | `StubAnalysisService` |
| `infrastructure` | Dış dünya uygulamaları (Sprint 2+) | scraper, LLM istemcisi |
| `api` | HTTP sınırı: route, şema, DI | `/analyze`, `/health` |

## Sprint planı

- **Sprint 1 ✅:** Uçtan uca iskelet — eklenti ↔ backend, stub analiz, testler.
- **Sprint 2 ✅:** Web scraping (BeautifulSoup + Playwright) ve veri katmanı + sağlamlık.
- **Sprint 3 ✅:** LLM entegrasyonu (Claude) + kural tabanlı, açıklanabilir lead scoring.
- **Sprint 4 ✅:** Soğuk e-posta + pitch üretimi, `/email` yeniden üretim, cila.

## Endpoint'ler

- `POST /analyze` — tam analiz: özet, acı noktaları, sinyaller, lead skoru, soğuk e-posta, pitch.
- `POST /email` — soğuk e-posta + pitch'i yeniden üretir (eklentideki "↻ Yeniden üret").
- `GET /health` — sağlık kontrolü. `GET /docs` — Swagger.

## Hızlı başlangıç

### 1) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# (Opsiyonel) Dinamik (JS) scraping için tarayıcı ikilisini kur:
playwright install chromium

# LLM sağlayıcısını seç ve anahtarını ver (ikisinden biri yeter):
#   Ücretsiz Gemini (Google AI Studio):
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=...              # https://aistudio.google.com/apikey
#   veya Claude:
# export LLM_PROVIDER=claude
# export ANTHROPIC_API_KEY=sk-ant-...

# Sunucuyu çalıştır
uvicorn app.main:app --reload --port 8000
```

> **Sağlayıcı değiştirmek için tek satır yeter:** `LLM_PROVIDER=claude` ↔
> `LLM_PROVIDER=gemini`. Kodun geri kalanı değişmez (provider-agnostic factory).
> OpenAI mimaride açık; ileride kolayca eklenebilir.

> **Zarif düşüş:** Playwright kurulmazsa statik scraping çalışmaya devam eder.
> **API anahtarı yoksa** sistem scraping-only moda düşer (özet/skor üretilmez,
> `is_stub: true`) — uygulama yine çalışır.

## LLM ve Lead Scoring (Sprint 3)

- **LLM (Claude veya Gemini):** Yalnızca dil/çıkarım işleri — şirket özeti, acı
  noktaları ve yapılandırılmış **sinyal çıkarımı** (sektör, işe alım, büyüme,
  teknoloji). `LLMProvider` portu ardında iki gerçek implementasyon var:
  `ClaudeLLMProvider` (forced tool use) ve `GeminiLLMProvider` (JSON modu).
  `LLM_PROVIDER` ile seçilir; kalan kod değişmez.
- **Lead Scoring:** **Kural tabanlı ve açıklanabilir** (Explainable AI) — makine
  öğrenmesi yok. LLM sadece sinyalleri çıkarır; puanı deterministik kural motoru
  verir ve her puanın gerekçesini (`reasons`) döndürür. Mimari, ileride aynı
  `ScoringEngine` arayüzü ardında XGBoost/LightGBM eklemeye açıktır.
- **Soğuk e-posta + pitch (Sprint 4):** Few-shot prompting ile **doğal, AI gibi
  görünmeyen** metin (klişe yasak listesi). Tek LLM; ikinci model yok. Satıcı
  profili `COPILOT_SELLER_NAME` / `COPILOT_SELLER_OFFERING` / `COPILOT_SELLER_REP_NAME`
  ile ayarlanır — modelin "ne sattığımızı" bilmesi için.

- Sağlık kontrolü: <http://localhost:8000/health>
- Otomatik API dokümanı (Swagger): <http://localhost:8000/docs>

### 2) Testler

```bash
cd backend
pytest
```

### 3) Chrome eklentisi

1. Chrome'da `chrome://extensions` adresine git.
2. Sağ üstten **Geliştirici modu**'nu aç.
3. **Paketlenmemiş öğe yükle** → `extension/` klasörünü seç.
4. Bir şirket sitesine gir, araç çubuğundaki eklenti ikonuna tıkla,
   **"Bu şirketi analiz et"** butonuna bas.

> Backend `http://localhost:8000` üzerinde çalışıyor olmalı. Adres
> `extension/config.js` ve `extension/manifest.json` içinden değiştirilebilir.

## Güvenlik notu

- API anahtarları **yalnızca backend'de** (`.env`) tutulur; eklentiye asla
  gömülmez. `.env` dosyası git'e eklenmez.
- **SSRF koruması:** Scraping'den önce URL doğrulanır; özel/iç ağ adreslerine
  (localhost, 10.x, 192.168.x, bulut metadata IP'leri) erişim engellenir.
- **Etik scraping:** robots.txt'e saygı gösterilir; gerçekçi bir tarayıcı
  User-Agent'ı kullanılır. (LinkedIn gibi ToS'u scraping'i yasaklayan siteler
  hedeflenmez. CAPTCHA/bot koruması AŞILMAZ — engellenen sitelere kullanıcıya
  anlaşılır bir mesaj gösterilir.)

## Scraping sağlamlığı

- Geçici hatalarda (timeout/bağlantı) üssel backoff'lu **yeniden deneme**.
- Aynı siteye art arda isteklerde **rate limiting** (nezaket).
- Ayrı connect/read **zaman aşımı** yönetimi.
- Tüm hatalar (403, timeout, DNS, SSL, bağlantı, robots.txt) **kullanıcı dostu,
  teknik olmayan** mesajlara çevrilir.
