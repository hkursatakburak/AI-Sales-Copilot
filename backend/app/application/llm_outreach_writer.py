"""Kişiselleştirilmiş soğuk e-posta ve toplantı pitch'i üretir (tek LLM ile).

Kullanıcının kritik şartı: e-posta YAPAY ZEKÂ tarafından yazılmış gibi
GÖRÜNMEMELİ. Doğal, kısa, samimi ve profesyonel olmalı; gerçek bir satış
temsilcisinin yazdığı hissini vermeli.

Yöntem (rehber + prompt engineering):
- Net rol + ton talimatı (deneyimli SDR).
- Klişe yasak listesi (hem Türkçe hem İngilizce kalıplar).
- Few-shot: iyi bir örnek e-posta ile tonu sabitleriz.
- Şirkete özgü TEK somut acı noktasına bağlan, TEK yumuşak CTA.
İkinci bir LLM kullanılmaz; her şey prompt mühendisliğiyle çözülür.
"""

from __future__ import annotations

import logging

from app.domain.interfaces import LLMProvider, OutreachWriter
from app.domain.models import CompanyInsights, SellerProfile

logger = logging.getLogger(__name__)

# Hem Türkçe hem İngilizce klişeler — model bunları KULLANMAMALI.
_BANNED_PHRASES = (
    "I hope this email finds you well",
    "We are excited",
    "Revolutionary",
    "As an AI",
    "Umarım bu e-posta sizi iyi bulur",
    "Umarım iyisinizdir",
    "Çok heyecanlıyız",
    "Devrim niteliğinde",
    "Bir yapay zekâ olarak",
    "Size özel bir fırsat",
)

# Few-shot: tonu sabitleyen iyi bir örnek (jenerik bir şirket için).
_EMAIL_EXAMPLE = (
    "Konu: Destek ekibiniz büyümeye yetişiyor mu?\n\n"
    "Merhaba,\n\n"
    "Kariyer sayfanızda aynı anda hem 4 mühendis hem 2 destek uzmanı ilanı "
    "gördüm — hızlı büyürken destek tarafının zorlanması çok normal.\n\n"
    "Biz tam burada işe yarıyoruz: ekiplerin tekrar eden müşteri araştırmasını "
    "otomatikleştiriyoruz, böylece insanlar asıl konuşmalara vakit ayırıyor.\n\n"
    "15 dakikalık kısa bir görüşmeye değer mi? Bu hafta uygun bir gününüz var mı?\n\n"
    "İyi çalışmalar,\nElif"
)


class LLMOutreachWriter(OutreachWriter):
    def __init__(
        self,
        provider: LLMProvider,
        seller: SellerProfile,
        *,
        email_max_tokens: int = 700,
        pitch_max_tokens: int = 700,
    ):
        self._provider = provider
        self._seller = seller
        self._email_max_tokens = email_max_tokens
        self._pitch_max_tokens = pitch_max_tokens

    async def write_cold_email(self, company_name: str, insights: CompanyInsights) -> str:
        return await self._provider.generate_text(
            system=self._email_system_prompt(),
            prompt=self._lead_context(company_name, insights),
            max_tokens=self._email_max_tokens,
        )

    async def write_pitch(self, company_name: str, insights: CompanyInsights) -> str:
        return await self._provider.generate_text(
            system=self._pitch_system_prompt(),
            prompt=self._lead_context(company_name, insights),
            max_tokens=self._pitch_max_tokens,
        )

    # --- Prompt'lar ---

    def _email_system_prompt(self) -> str:
        banned = "\n".join(f"- {p}" for p in _BANNED_PHRASES)
        return (
            f"Sen {self._seller.name} firmasında deneyimli bir satış temsilcisisin. "
            f"Sattığın şey: {self._seller.offering}\n\n"
            "Sana bir potansiyel müşteri (lead) hakkında bilgi verilecek. Görevin: "
            "gerçek bir insanın yazdığı gibi, KISA ve DOĞAL bir soğuk e-posta yazmak.\n\n"
            "KURALLAR:\n"
            "- 110 kelimeyi geçme. Kısa paragraflar kullan.\n"
            "- Şirkete özgü TEK somut detaya/acı noktasına değin (genel laf etme).\n"
            "- Samimi ama profesyonel ol; satışçı/abartılı dilden kaçın.\n"
            "- TEK yumuşak çağrı (CTA): kısa bir görüşme öner.\n"
            f"- İmzayı '{self._seller.rep_name}' olarak at.\n"
            "- Türkçe yaz. 'Konu:' satırıyla başla.\n"
            "- Yapay zekâ tarafından yazıldığı belli OLMAMALI.\n\n"
            "ASLA şu klişeleri kullanma:\n"
            f"{banned}\n\n"
            "İşte tonu doğru yakalayan bir örnek (birebir kopyalama, sadece tonu örnek al):\n"
            f"---\n{_EMAIL_EXAMPLE}\n---\n\n"
            "Sadece e-postayı döndür; açıklama veya ek yorum ekleme."
        )

    def _pitch_system_prompt(self) -> str:
        return (
            f"Sen {self._seller.name} firmasında bir satış temsilcisisin. "
            f"Sattığın şey: {self._seller.offering}\n\n"
            "Bir potansiyel müşteriyle yapılacak görüşmeye hazırlanıyorsun. Görevin: "
            "bu şirkete özel, 4-5 maddelik KISA konuşma noktaları hazırlamak.\n\n"
            "KURALLAR:\n"
            "- Her madde tek cümle, somut ve bu şirkete özgü olsun.\n"
            "- Acı noktalarını bizim çözümümüze bağla.\n"
            "- Klişe ve abartıdan kaçın; doğal, güvenli bir ton kullan.\n"
            "- Türkçe yaz. Maddeleri '- ' ile listele.\n\n"
            "Sadece konuşma noktalarını döndür."
        )

    @staticmethod
    def _lead_context(company_name: str, insights: CompanyInsights) -> str:
        s = insights.signals
        pain = "\n".join(f"- {p}" for p in insights.pain_points) or "- (belirtilmemiş)"
        return (
            f"ŞİRKET: {company_name}\n"
            f"ÖZET: {insights.summary}\n"
            f"OLASI ACI NOKTALARI:\n{pain}\n"
            f"SEKTÖR: {s.sector or '-'}\n"
            f"ÇALIŞAN BANDI: {s.employee_band or '-'}\n"
            f"İŞE ALIM: {'evet' if s.is_hiring else 'hayır'}"
            f"{(' (' + ', '.join(s.hiring_roles) + ')') if s.hiring_roles else ''}\n"
            f"BÜYÜME SİNYALLERİ: {', '.join(s.growth_signals) or '-'}\n"
            f"TEKNOLOJİLER: {', '.join(s.technologies) or '-'}"
        )
