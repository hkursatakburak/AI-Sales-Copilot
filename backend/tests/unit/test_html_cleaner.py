"""HTML temizleyici (`clean_html`) testleri."""

from __future__ import annotations

from app.infrastructure.scraping.html_cleaner import clean_html

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
  <head>
    <title>Acme Corp | Anasayfa</title>
    <meta name="description" content="Acme yazılım çözümleri sunar." />
    <meta property="og:site_name" content="Acme Corp" />
    <style>.x { color: red; }</style>
  </head>
  <body>
    <nav>Menü Hakkımızda İletişim</nav>
    <header>Üst başlık gürültüsü</header>
    <main>
      <h1>Geleceğin Yazılımı</h1>
      <h2>Ürünlerimiz</h2>
      <p>Acme, ölçeklenebilir bulut çözümleri geliştirir.</p>
      <script>console.log("izlenmemeli");</script>
    </main>
    <footer>Telif hakkı 2026</footer>
  </body>
</html>
"""


def test_extracts_title_and_site_name() -> None:
    doc = clean_html(SAMPLE_HTML)
    assert doc.title == "Acme Corp | Anasayfa"
    assert doc.site_name == "Acme Corp"


def test_extracts_meta_description() -> None:
    doc = clean_html(SAMPLE_HTML)
    assert doc.meta_description == "Acme yazılım çözümleri sunar."


def test_extracts_headings() -> None:
    doc = clean_html(SAMPLE_HTML)
    assert "Geleceğin Yazılımı" in doc.headings
    assert "Ürünlerimiz" in doc.headings


def test_removes_noise_tags() -> None:
    doc = clean_html(SAMPLE_HTML)
    assert "console.log" not in doc.text
    assert "izlenmemeli" not in doc.text
    assert "Menü" not in doc.text  # nav atıldı
    assert "Telif hakkı" not in doc.text  # footer atıldı


def test_keeps_main_content() -> None:
    doc = clean_html(SAMPLE_HTML)
    assert "ölçeklenebilir bulut çözümleri" in doc.text


def test_collapses_whitespace() -> None:
    doc = clean_html("<p>çok    boşluklu\n\n  metin</p>")
    assert "  " not in doc.text
    assert doc.text == "çok boşluklu metin"


def test_handles_missing_meta_gracefully() -> None:
    doc = clean_html("<html><body><p>sade</p></body></html>")
    assert doc.title is None
    assert doc.site_name is None
    assert doc.meta_description is None
    assert doc.text == "sade"
