"""Yapılandırılmış (structured) loglama altyapısı.

Her gelen istek için bir `request_id` üretilir ve `contextvar` ile o isteğe
ait tüm log satırlarına otomatik eklenir. Böylece üretimde bir hatayı tek bir
isteğin tüm akışı boyunca takip edebiliriz (gözlemlenebilirlik / observability).
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

# İsteğe özel bağlam. Middleware her istekte bunu doldurur.
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str:
    return _request_id_ctx.get()


class RequestIdFilter(logging.Filter):
    """Aktif `request_id`'yi her log kaydına enjekte eden filtre."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Kök logger'ı tek seferlik yapılandırır.

    Aynı handler'ların tekrar tekrar eklenmesini önlemek için mevcut
    handler'lar temizlenir (örn. testlerde app birden çok kez kurulabilir).
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(handler)
