from __future__ import annotations

import json
import logging
from app.domain.interfaces import LLMProvider

logger = logging.getLogger(__name__)


class DemoLLMProvider(LLMProvider):
    async def extract_structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        tool_name: str,
        tool_description: str,
    ) -> dict:
        prompt_lower = prompt.lower()

        if "otokar" in prompt_lower:
            return {
                "summary": "Otokar, Türkiye'nin lider askeri araç ve ticari araç üreticisidir. Otobüs, kamyon, zırhlı araçlar ve savunma sanayi çözümleri geliştirmektedir. Koç Grubu bünyesinde faaliyet göstermektedir.",
                "pain_points": [
                    "Gelişen küresel savunma ihalelerinde hızlı teslimat ve ölçeklenebilirlik ihtiyacı.",
                    "Ticari araç pazarında elektrikli ve otonom teknolojilere geçişin yüksek Ar-Ge maliyetleri."
                ],
                "signals": {
                    "sector": "Savunma ve Otomotiv",
                    "employee_band": "1000+",
                    "is_hiring": True,
                    "hiring_roles": ["Yazılım Mühendisi", "Tasarım Mühendisi", "Satış Yöneticisi"],
                    "growth_signals": ["Yeni elektrikli otobüs ihracatı sözleşmesi imzalandı", "Savunma sanayinde yeni ihracat lisansı alındı"],
                    "technologies": ["SAP", "Python", "AutoCAD", "Kubernetes"]
                }
            }
        elif "github" in prompt_lower:
            return {
                "summary": "GitHub, yazılım geliştirme projeleri için barındırma, sürüm kontrolü ve işbirliği sağlayan lider bir platformdur. Git tabanlı çalışan platform, milyonlarca yazılımcıya ve kurumsal firmaya ev sahipliği yapar.",
                "pain_points": [
                    "Büyük ölçekli kurumsal takımlarda kod inceleme (PR) sürelerinin uzaması.",
                    "Geliştiricilerin rutin işlerden dolayı yaratıcı kodlamaya az vakit bulması."
                ],
                "signals": {
                    "sector": "SaaS / Yazılım",
                    "employee_band": "1000+",
                    "is_hiring": True,
                    "hiring_roles": ["Site Reliability Engineer", "Security Analyst", "Account Executive"],
                    "growth_signals": ["GitHub Copilot kullanımında rekor artış", "Kurumsal bulut gelirlerinde büyüme"],
                    "technologies": ["Ruby on Rails", "React", "Go", "Kubernetes", "Azure"]
                }
            }
        else:
            return {
                "summary": "Example Domain, test ve eğitim amaçlı tasarlanmış örnek bir web sitesidir. İnternet standartlarında belgelerde ve teknik testlerde sıkça referans olarak kullanılır.",
                "pain_points": [
                    "Statik ve basit yapısı nedeniyle modern interaktif kullanıcı deneyimi sunamaması.",
                    "Herhangi bir ticari ürün veya servis sunmadığı için doğrudan gelir elde etme modeli olmaması."
                ],
                "signals": {
                    "sector": "Eğitim / Test",
                    "employee_band": "1-10",
                    "is_hiring": False,
                    "hiring_roles": [],
                    "growth_signals": ["İnternet standartlarında kullanım sıklığı kararlı"],
                    "technologies": ["HTML5", "CSS3", "DNSSEC"]
                }
            }

    async def generate_text(self, *, system: str, prompt: str, max_tokens: int) -> str:
        prompt_lower = prompt.lower()
        is_pitch = "pitch" in prompt_lower or "toplantı" in prompt_lower or "sunum" in prompt_lower

        if "otokar" in prompt_lower:
            if is_pitch:
                return (
                    "1. Giriş: Otokar'ın elektrikli otobüs ve askeri araç ihracatındaki liderliği.\n"
                    "2. Değer Önerisi: AI Sales Copilot ile B2B satış ekiplerinin araştırma süresini %80 azaltmak.\n"
                    "3. Kanıt: Diğer kurumsal otomotiv tedarikçileriyle yapılan iş ortaklıkları."
                )
            else:
                return (
                    "Sayın Otokar Satış Yöneticisi,\n\n"
                    "Otokar'ın ticari araçlar ve savunma sanayindeki öncü konumunu yakından takip ediyoruz. Özellikle son elektrikli otobüs ihracatı başarılarınız, ekibinizin vizyonunu net bir şekilde ortaya koyuyor.\n\n"
                    "Satış ekiplerinizin potansiyel müşteri araştırmasını ve kişiselleştirilmiş ulaşım metni yazımını saniyeler içinde yapan yapay zeka asistanımız AI Sales Copilot ile satış süreçlerinizi hızlandırmak isteriz.\n\n"
                    "Uygun bir zamanda 10 dakikalık bir demo görüşmesi yapabilir miyiz?\n\n"
                    "Saygılarımla,\n"
                    "Elif"
                )
        elif "github" in prompt_lower:
            if is_pitch:
                return (
                    "1. Giriş: GitHub'ın geliştirici dünyasındaki pazar liderliği.\n"
                    "2. Değer Önerisi: Satış ekipleri için saniyeler içinde B2B şirket içgörüsü ve lead skoru çıkarma.\n"
                    "3. Kapanış: 10 dakikalık bir demo teklifi."
                )
            else:
                return (
                    "Sayın GitHub Satış Yöneticisi,\n\n"
                    "GitHub'ın yazılım ekosistemini yönlendiren liderliğini büyük bir hayranlıkla izliyoruz. Son dönemde kurumsal bulut alanındaki büyümeniz oldukça heyecan verici.\n\n"
                    "Satış ekiplerinizin kurumsal müşteri araştırmalarını saniyeler seviyesine indiren AI Sales Copilot ile tanıştırmak isteriz. Bu sayede reps'leriniz PR ve teknik araştırmalar yerine doğrudan satışı kapatmaya odaklanabilir.\n\n"
                    "Kısa bir demo için uygun zamanınızı paylaşabilir misiniz?\n\n"
                    "Saygılarımla,\n"
                    "Elif"
                )
        else:
            if is_pitch:
                return (
                    "1. Giriş: Example Domain, test ve doğrulama süreçlerinde yaygın referans.\n"
                    "2. Değer Önerisi: AI Sales Copilot ile hızlı B2B lead analizi doğrulama.\n"
                    "3. Kapanış: Teknik akışın başarısı."
                )
            else:
                return (
                    "Merhaba,\n\n"
                    "Example Domain'in internet ekosistemindeki benzersiz yerini ve test süreçlerindeki önemini takdir ediyoruz.\n\n"
                    "Satış ekipleriniz için geliştirdiğimiz AI Sales Copilot asistanımızı size sunmaktan mutluluk duyarız. Hızlı entegrasyonu denemek ister misiniz?\n\n"
                    "Saygılarımla,\n"
                    "Elif"
                )
