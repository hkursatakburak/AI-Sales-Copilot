"""Alan arayüzleri (ports) — bağımlılıkların tersine çevrilmesi (DIP).

SOLID'in "D"si (Dependency Inversion Principle): üst seviye iş mantığı,
alt seviye detaylara (somut scraping/LLM sınıflarına) değil; soyutlamalara
(bu arayüzlere) bağımlı olur. API katmanı `AnalysisService` arayüzünü ister;
hangi somut uygulamanın geldiğini bilmez. Sprint 1'de `StubAnalysisService`,
Sprint 4'te gerçek pipeline gelecek — API kodu hiç değişmeyecek.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import (
    CompanyAnalysis,
    CompanyInsights,
    CompanySignals,
    LeadScore,
    ScrapedContent,
)


class AnalysisService(ABC):
    """Bir şirket URL'sini eksiksiz bir analize dönüştüren servisin sözleşmesi."""

    @abstractmethod
    async def analyze(self, url: str) -> CompanyAnalysis:
        """Verilen URL için bir `CompanyAnalysis` üretir.

        Async tanımlandı çünkü gerçek uygulamalar (scraping + LLM çağrıları)
        G/Ç-yoğun (I/O-bound) olacak; baştan async tasarlamak ileride
        senkron->async geçişinin acısını önler.
        """
        raise NotImplementedError


class WebScraper(ABC):
    """Bir URL'yi temizlenmiş `ScrapedContent`'e dönüştüren scraper sözleşmesi.

    Bu arayüz sayesinde üst katman, içeriğin nasıl çekildiğini (statik istek,
    tarayıcı render'ı veya ikisinin melezi) bilmez. Strategy deseni: aynı
    sözleşmeyi farklı implementasyonlar (BeautifulSoup / Playwright / Hybrid)
    karşılar; biri diğeriyle sorunsuz değiştirilebilir.
    """

    @abstractmethod
    async def scrape(self, url: str) -> ScrapedContent:
        raise NotImplementedError


class LLMProvider(ABC):
    """Sağlayıcıdan bağımsız LLM erişim sözleşmesi (port).

    Üst katman hangi LLM'in (Claude/Gemini/OpenAI) kullanıldığını bilmez. Bu
    sayede sağlayıcı, somut implementasyon değiştirilerek takas edilebilir.
    """

    @abstractmethod
    async def extract_structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        tool_name: str,
        tool_description: str,
    ) -> dict:
        """Verilen JSON şemasına uyan yapılandırılmış bir sözlük döndürür."""
        raise NotImplementedError


class CompanyInsightAnalyzer(ABC):
    """Çekilen içerikten `CompanyInsights` üreten analizci sözleşmesi."""

    @abstractmethod
    async def analyze(self, content: ScrapedContent) -> CompanyInsights:
        raise NotImplementedError


class ScoringEngine(ABC):
    """Sinyallerden lead skoru üreten motor sözleşmesi.

    Senkron ve yan etkisizdir (saf hesap). Sprint 3'te kural tabanlı bir
    implementasyon gelir; aynı arayüz ileride XGBoost/LightGBM tabanlı bir
    motorla değiştirilebilir (kullanıcının şartı).
    """

    @abstractmethod
    def score(self, signals: CompanySignals) -> LeadScore:
        raise NotImplementedError
