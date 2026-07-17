"""MultiPageCrawler testleri — ağ kullanmadan."""

from __future__ import annotations

import pytest

from app.core.exceptions import ScrapeError
from app.domain.interfaces import WebScraper
from app.domain.models import ScrapedContent
from app.infrastructure.scraping.multi_page_crawler import MultiPageCrawler
from tests.factories import make_scraped_content


class MappingScraper(WebScraper):
    """URL'e göre farklı içerik döndüren test yardımcısı."""

    def __init__(
        self,
        mapping: dict[str, ScrapedContent],
        default_error: Exception | None = None,
    ) -> None:
        self._mapping = mapping
        self._default_error = default_error

    async def scrape(self, url: str) -> ScrapedContent:
        key = url.rstrip("/")
        for k, v in self._mapping.items():
            if k.rstrip("/") == key:
                return v
        if self._default_error:
            raise self._default_error
        raise ScrapeError(f"Bilinmeyen URL: {url}")


def _rich(url: str, text: str) -> ScrapedContent:
    words = text.split()
    return make_scraped_content(url=url, text=text, word_count=len(words))


@pytest.mark.asyncio
async def test_merges_subpages_into_main_content() -> None:
    main = _rich("https://example.com", "ana sayfa metni " * 30)
    about = _rich("https://example.com/about", "hakkımızda metni " * 30)

    scraper = MappingScraper(
        {"https://example.com": main, "https://example.com/about": about},
        default_error=ScrapeError("404"),
    )
    crawler = MultiPageCrawler(scraper, max_subpages=1, min_words=50)
    result = await crawler.scrape("https://example.com")

    assert "ana sayfa metni" in result.text
    assert "hakkımızda metni" in result.text
    assert result.url == "https://example.com"


@pytest.mark.asyncio
async def test_returns_main_when_all_subpages_fail() -> None:
    main = _rich("https://example.com", "ana sayfa " * 20)
    scraper = MappingScraper(
        {"https://example.com": main},
        default_error=ScrapeError("404"),
    )
    crawler = MultiPageCrawler(scraper, max_subpages=4, min_words=50)
    result = await crawler.scrape("https://example.com")

    assert result.text == main.text
    assert result.word_count == main.word_count


@pytest.mark.asyncio
async def test_skips_thin_subpages() -> None:
    main = _rich("https://example.com", "ana sayfa metni " * 20)
    thin = make_scraped_content(
        url="https://example.com/about", text="az", word_count=1
    )
    scraper = MappingScraper(
        {"https://example.com": main, "https://example.com/about": thin},
        default_error=ScrapeError("404"),
    )
    crawler = MultiPageCrawler(scraper, max_subpages=1, min_words=50)
    result = await crawler.scrape("https://example.com")

    assert result.text == main.text


@pytest.mark.asyncio
async def test_respects_max_subpages() -> None:
    call_log: list[str] = []
    rich_content = _rich("https://example.com", "içerik " * 30)

    class LoggingScraper(WebScraper):
        async def scrape(self, url: str) -> ScrapedContent:
            call_log.append(url)
            return rich_content

    crawler = MultiPageCrawler(LoggingScraper(), max_subpages=2, min_words=50)
    await crawler.scrape("https://example.com")

    assert len(call_log) == 3  # 1 ana + 2 alt sayfa


@pytest.mark.asyncio
async def test_skips_failed_subpages_gracefully() -> None:
    main = _rich("https://example.com", "ana sayfa " * 30)
    about = _rich("https://example.com/about", "hakkımızda " * 60)

    class PartialScraper(WebScraper):
        async def scrape(self, url: str) -> ScrapedContent:
            if url.rstrip("/") == "https://example.com":
                return main
            if "/about" in url:
                return about
            raise ScrapeError("bulunamadı")

    crawler = MultiPageCrawler(PartialScraper(), max_subpages=4, min_words=50)
    result = await crawler.scrape("https://example.com")

    assert "ana sayfa" in result.text
    assert "hakkımızda" in result.text


@pytest.mark.asyncio
async def test_metadata_comes_from_main_page() -> None:
    main = make_scraped_content(
        url="https://example.com",
        title="Ana Başlık",
        site_name="ExampleCo",
        text="ana metni " * 20,
        word_count=200,
        detected_name="Example Company",
    )
    about = make_scraped_content(
        url="https://example.com/about",
        title="Hakkımızda",
        site_name="Farklı İsim",
        text="alt sayfa metni " * 20,
        word_count=80,
    )
    scraper = MappingScraper(
        {"https://example.com": main, "https://example.com/about": about},
        default_error=ScrapeError("404"),
    )
    crawler = MultiPageCrawler(scraper, max_subpages=1, min_words=50)
    result = await crawler.scrape("https://example.com")

    assert result.title == "Ana Başlık"
    assert result.site_name == "ExampleCo"
    assert result.detected_name == "Example Company"
    assert result.url == "https://example.com"


@pytest.mark.asyncio
async def test_entry_url_not_duplicated_as_candidate() -> None:
    """Ana URL zaten /about ise, /about tekrar çekilmemeli."""
    call_log: list[str] = []
    content = _rich("https://example.com/about", "içerik " * 30)

    class LoggingScraper(WebScraper):
        async def scrape(self, url: str) -> ScrapedContent:
            call_log.append(url)
            return content

    crawler = MultiPageCrawler(LoggingScraper(), max_subpages=4, min_words=50)
    await crawler.scrape("https://example.com/about")

    called_paths = [url for url in call_log if url.rstrip("/") == "https://example.com/about"]
    assert len(called_paths) == 1  # yalnızca bir kez çekildi
