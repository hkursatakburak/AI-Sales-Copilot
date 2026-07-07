"""API şema yardımcıları — özellikle okunabilir preview üretimi."""

from __future__ import annotations

from app.api.schemas import ScrapedContentSchema
from tests.factories import make_scraped_content


def test_preview_prefers_meta_description() -> None:
    desc = "Bu şirket bulut tabanlı yazılım çözümleri sunar ve hızla büyümektedir."
    schema = ScrapedContentSchema.from_domain(
        make_scraped_content(meta_description=desc, text="x" * 1000)
    )
    assert schema.content_preview == desc


def test_preview_uses_text_when_meta_too_short() -> None:
    schema = ScrapedContentSchema.from_domain(
        make_scraped_content(meta_description="kısa", text="tam metin içeriği")
    )
    assert schema.content_preview == "tam metin içeriği"


def test_preview_truncates_long_text_on_word_boundary() -> None:
    long_text = "kelime " * 200  # >> 320 karakter
    schema = ScrapedContentSchema.from_domain(
        make_scraped_content(meta_description=None, text=long_text)
    )
    assert schema.content_preview.endswith("…")
    assert len(schema.content_preview) <= ScrapedContentSchema.PREVIEW_CHARS + 1
    # Kelime ortadan bölünmemeli (son karakter '…' hariç boşlukla bitmeli değil).
    assert "  " not in schema.content_preview
