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

- **Sprint 1 (bu sürüm):** Uçtan uca iskelet — eklenti ↔ backend, stub analiz, testler.
- **Sprint 2:** Web scraping (BeautifulSoup + Playwright) ve veri katmanı.
- **Sprint 3:** LLM entegrasyonu (Claude) + kural tabanlı, açıklanabilir lead scoring.
- **Sprint 4:** Soğuk e-posta + pitch üretimi, orkestrasyon, cila.

## Hızlı başlangıç

### 1) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# (Opsiyonel) Dinamik (JS) scraping için tarayıcı ikilisini kur:
playwright install chromium

# Sunucuyu çalıştır
uvicorn app.main:app --reload --port 8000
```

> Playwright kurulmazsa sorun olmaz: statik scraping (BeautifulSoup) çalışır,
> dinamik yedek devre dışı kalır (zarif düşüş).

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
- **Etik scraping:** robots.txt'e saygı gösterilir; tanımlı bir User-Agent
  kullanılır. (LinkedIn gibi ToS'u scraping'i yasaklayan siteler hedeflenmez.)
