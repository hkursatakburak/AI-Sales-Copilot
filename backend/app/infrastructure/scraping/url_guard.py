"""URL güvenlik denetimi — SSRF (Server-Side Request Forgery) koruması.

Kullanıcı backend'e rastgele bir URL verip onu çektirdiği için, kötü niyetli
biri bunu iç ağ adreslerini taramak veya bulut metadata servislerine
(örn. http://169.254.169.254 — AWS kimlik bilgileri!) ulaşmak için
kullanabilir. Bu sınıf, scraping'den ÖNCE adresi doğrular:

- Yalnızca http/https şemasına izin verir.
- Hostname'i çözer ve özel/loopback/link-local/reserved IP'leri reddeder.

`is_blocked_ip` saf (yan etkisiz) bir fonksiyondur; bu yüzden ağ olmadan
kolayca test edilir.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.exceptions import ScrapeError

_ALLOWED_SCHEMES = {"http", "https"}


class UrlGuard:
    def __init__(self, allow_private: bool = False):
        self.allow_private = allow_private

    @staticmethod
    def is_blocked_ip(ip_str: str) -> bool:
        """Bir IP adresinin (string) güvensiz/iç ağ olup olmadığını söyler."""
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )

    def validate(self, url: str) -> None:
        """URL güvensizse `ScrapeError` fırlatır; güvenliyse sessizce döner."""
        parsed = urlparse(url)

        if parsed.scheme not in _ALLOWED_SCHEMES:
            raise ScrapeError(f"Desteklenmeyen URL şeması: '{parsed.scheme}'.")

        host = parsed.hostname
        if not host:
            raise ScrapeError("URL'de geçerli bir host bulunamadı.")

        if self.allow_private:
            return  # Yerel geliştirme: DNS çözümü ve IP kontrolü atlanır.

        try:
            addr_infos = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise ScrapeError(f"Host çözümlenemedi: {host}") from exc

        for info in addr_infos:
            ip_str = info[4][0]
            if self.is_blocked_ip(ip_str):
                raise ScrapeError(
                    f"Güvenlik: özel/iç ağ adresine erişim engellendi ({host} -> {ip_str})."
                )
