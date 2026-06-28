"""Gerçekçi tarayıcı HTTP başlıkları.

Birçok site, eksik/şüpheli başlıklara sahip istekleri (örn. yalnızca
User-Agent gönderen kaba botlar) reddeder. Gerçek bir tarayıcının
gönderdiği standart başlıkları taklit etmek, BASİT filtreleri geçmeye
yardımcı olur. Bu, standart HTTP davranışıdır — CAPTCHA çözme veya gelişmiş
bot korumalarını aşma DEĞİLDİR (onlar bilinçli olarak kapsam dışıdır).
"""

from __future__ import annotations


def browser_headers(user_agent: str) -> dict[str, str]:
    return {
        "User-Agent": user_agent,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
