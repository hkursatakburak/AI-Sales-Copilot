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


# --- Şirket adı öncelik sırası ---


def test_company_name_prefers_json_ld() -> None:
    html = """
    <html><head>
    <title>Farklı Başlık | X</title>
    <meta property="og:site_name" content="OG Adı" />
    <script type="application/ld+json">
      {"@context":"https://schema.org","@type":"Organization","name":"Acme A.Ş."}
    </script>
    </head><body><h1>H1 Adı</h1></body></html>
    """
    assert clean_html(html).company_name == "Acme A.Ş."


def test_company_name_json_ld_in_graph() -> None:
    html = """
    <html><head><script type="application/ld+json">
      {"@graph":[{"@type":"WebPage"},{"@type":"Organization","name":"Graf Ltd."}]}
    </script></head><body></body></html>
    """
    assert clean_html(html).company_name == "Graf Ltd."


def test_company_name_falls_back_to_og_site_name() -> None:
    html = '<html><head><meta property="og:site_name" content="OG Şirket" />' \
           "<title>Başlık | Sayfa</title></head><body></body></html>"
    assert clean_html(html).company_name == "OG Şirket"


def test_company_name_falls_back_to_title_prefix() -> None:
    html = "<html><head><title>Acme Corp | Anasayfa</title></head><body></body></html>"
    assert clean_html(html).company_name == "Acme Corp"


def test_company_name_falls_back_to_h1() -> None:
    html = "<html><head></head><body><h1>Sadece H1 A.Ş.</h1></body></html>"
    assert clean_html(html).company_name == "Sadece H1 A.Ş."


def test_company_name_none_when_nothing() -> None:
    assert clean_html("<html><body><p>metin</p></body></html>").company_name is None


def test_strips_control_characters() -> None:
    # Bozuk kodlama artıkları (kontrol karakterleri + U+FFFD) metinden atılmalı.
    doc = clean_html("<p>merhaba\x00\x07 d�nya</p>")
    assert "\x00" not in doc.text
    assert "�" not in doc.text
    assert "merhaba" in doc.text
