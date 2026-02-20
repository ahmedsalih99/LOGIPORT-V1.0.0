# services/tafqit_service.py
# Spells numbers in words (AR/EN/TR) including currency main & fractional units.
# Exposes: tafqit(amount, currency_code, lang)

from typing import Tuple

# ------------------------------------------------------------------
# UNIFIED CURRENCY DEFINITIONS (single source of truth)
# ------------------------------------------------------------------

CURRENCIES = {
    "USD": {
        "ar": ("دولار أمريكي", "سنت"),
        "en": ("US dollars", "cents"),
        "tr": ("Amerikan doları", "sent"),
    },
    "EUR": {
        "ar": ("يورو", "سنت"),
        "en": ("euros", "cents"),
        "tr": ("euro", "sent"),
    },
    "TRY": {
        "ar": ("ليرة تركية", "قرش"),
        "en": ("Turkish liras", "kuruş"),
        "tr": ("Türk lirası", "kuruş"),
    },
    "GBP": {
        "ar": ("جنيه إسترليني", "بنس"),
        "en": ("pounds sterling", "pence"),
        "tr": ("İngiliz sterlini", "peni"),
    },
    "SAR": {
        "ar": ("ريال سعودي", "هللة"),
        "en": ("Saudi riyals", "halalas"),
        "tr": ("Suudi riyali", "halala"),
    },
    "AED": {
        "ar": ("درهم إماراتي", "فلس"),
        "en": ("UAE dirhams", "fils"),
        "tr": ("BAE dirhemi", "fils"),
    },
    "RUB": {
        "ar": ("روبل روسي", "كوبيك"),
        "en": ("Russian rubles", "kopeks"),
        "tr": ("Rus rublesi", "kopek"),
    },
    "CNY": {
        "ar": ("يوان صيني", "فين"),
        "en": ("Chinese yuan", "fen"),
        "tr": ("Çin yuanı", "fen"),
    },
    "JPY": {
        "ar": ("ين ياباني", "سين"),
        "en": ("Japanese yen", "sen"),
        "tr": ("Japon yeni", "sen"),
    },
    "IQD": {
        "ar": ("دينار عراقي", "فلس"),
        "en": ("Iraqi dinars", "fils"),
        "tr": ("Irak dinarı", "fils"),
    },
    "EGP": {
        "ar": ("جنيه مصري", "قرش"),
        "en": ("Egyptian pounds", "piastres"),
        "tr": ("Mısır lirası", "kuruş"),
    },
    "JOD": {
        "ar": ("دينار أردني", "فلس"),
        "en": ("Jordanian dinars", "fils"),
        "tr": ("Ürdün dinarı", "fils"),
    },
    "KWD": {
        "ar": ("دينار كويتي", "فلس"),
        "en": ("Kuwaiti dinars", "fils"),
        "tr": ("Kuveyt dinarı", "fils"),
    },
    "OMR": {
        "ar": ("ريال عماني", "بيسة"),
        "en": ("Omani rials", "baisa"),
        "tr": ("Umman riyali", "baisa"),
    },
    "BHD": {
        "ar": ("دينار بحريني", "فلس"),
        "en": ("Bahraini dinars", "fils"),
        "tr": ("Bahreyn dinarı", "fils"),
    },
    "QAR": {
        "ar": ("ريال قطري", "درهم"),
        "en": ("Qatari riyals", "dirhams"),
        "tr": ("Katar riyali", "dirhem"),
    },
}


def currency_names(code: str, lang: str) -> Tuple[str, str]:
    code = (code or "").upper()
    lang = (lang or "en").lower()

    cur = CURRENCIES.get(code)
    if not cur:
        if lang == "ar":
            return (code or "عملة", "سنت")
        if lang == "tr":
            return (code or "para birimi", "sent")
        return (code or "currency", "cents")

    return cur.get(lang) or cur["en"]


# ------------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------------

def tafqit(amount: float, currency_code: str, lang: str) -> str:
    """Convert numeric amount to words with currency in the given language."""
    return TafqitService().amount_in_words(amount, currency_code, lang)


class TafqitService:
    def amount_in_words(self, amount: float, currency_code: str, lang: str) -> str:
        lang = (lang or "en").lower()
        amount = float(amount or 0)
        integer = int(abs(amount))
        fraction = int(round((abs(amount) - integer) * 100))

        cur_main, cur_frac = currency_names(currency_code, lang)

        if lang == "ar":
            words_int = number_to_words_ar(integer) if integer != 0 else "صفر"
            if fraction > 0:
                words_frac = number_to_words_ar(fraction)
                return f"{words_int} {cur_main} و {words_frac} {cur_frac}".strip()
            return f"{words_int} {cur_main}".strip()

        if lang == "tr":
            words_int = number_to_words_tr(integer) if integer != 0 else "sıfır"
            if fraction > 0:
                words_frac = number_to_words_tr(fraction)
                return f"{words_int} {cur_main} ve {words_frac} {cur_frac}".strip()
            return f"{words_int} {cur_main}".strip()

        # default EN
        words_int = number_to_words_en(integer) if integer != 0 else "zero"
        if fraction > 0:
            words_frac = number_to_words_en(fraction)
            return f"{words_int} {cur_main} and {words_frac} {cur_frac}".strip()
        return f"{words_int} {cur_main}".strip()


# ------------------------------------------------------------------
# NUMBER → WORDS (EN / TR / AR)
# ------------------------------------------------------------------

def number_to_words_en(n: int) -> str:
    if n == 0:
        return "zero"
    ones = ["","one","two","three","four","five","six","seven","eight","nine",
            "ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen"]
    tens = ["","","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]
    scales = ["","thousand","million","billion"]

    def words_1_999(x):
        w = []
        if x >= 100:
            w.append(ones[x//100]); w.append("hundred"); x%=100
            if x: w.append("and")
        if x >= 20:
            w.append(tens[x//10]); x%=10
            if x: w.append(ones[x])
        elif x > 0:
            w.append(ones[x])
        return " ".join(w)

    parts = []
    scale_idx = 0
    while n > 0:
        chunk = n % 1000
        if chunk:
            txt = words_1_999(chunk)
            if scales[scale_idx]:
                txt += f" {scales[scale_idx]}"
            parts.append(txt)
        n //= 1000
        scale_idx += 1
    return " ".join(reversed(parts))


def number_to_words_tr(n: int) -> str:
    if n == 0:
        return "sıfır"
    ones = ["","bir","iki","üç","dört","beş","altı","yedi","sekiz","dokuz"]
    tens = ["","on","yirmi","otuz","kırk","elli","altmış","yetmiş","seksen","doksan"]
    scales = ["","bin","milyon","milyar"]

    def words_1_999(x):
        w = []
        if x >= 100:
            if x//100 == 1:
                w.append("yüz")
            else:
                w.extend([ones[x//100],"yüz"])
            x%=100
        if x >= 10:
            w.append(tens[x//10]); x%=10
        if x > 0:
            w.append(ones[x])
        return " ".join(w)

    parts = []
    idx = 0
    while n > 0:
        chunk = n % 1000
        if chunk:
            txt = words_1_999(chunk)
            scale = scales[idx]
            if idx == 1 and chunk == 1:
                txt = "bin"
            elif scale:
                txt += f" {scale}"
            parts.append(txt)
        n//=1000; idx+=1
    return " ".join(reversed(parts))


def number_to_words_ar(n: int) -> str:
    if n == 0:
        return "صفر"
    ones = ["","واحد","اثنان","ثلاثة","أربعة","خمسة","ستة","سبعة","ثمانية","تسعة",
            "عشرة","أحد عشر","اثنا عشر","ثلاثة عشر","أربعة عشر","خمسة عشر","ستة عشر","سبعة عشر","ثمانية عشر","تسعة عشر"]
    tens = ["","عشرة","عشرون","ثلاثون","أربعون","خمسون","ستون","سبعون","ثمانون","تسعون"]
    hundreds = ["","مئة","مئتان","ثلاثمئة","أربعمئة","خمسمئة","ستمئة","سبعمئة","ثمانمئة","تسعمئة"]

    def words_1_99(x):
        if x < 20:
            return ones[x]
        t, u = divmod(x, 10)
        if u == 0:
            return tens[t]
        return f"{ones[u]} و {tens[t]}"

    def words_1_999(x):
        h, r = divmod(x, 100)
        parts = []
        if h:
            parts.append(hundreds[h])
        if r:
            parts.append(words_1_99(r))
        return " و ".join(parts)

    millions, rem = divmod(n, 1_000_000)
    thousands, hundreds_ = divmod(rem, 1000)

    parts = []

    if millions:
        if millions == 1:
            parts.append("مليون")
        elif millions == 2:
            parts.append("مليونان")
        elif 3 <= millions <= 10:
            parts.append(f"{words_1_999(millions)} ملايين")
        else:
            parts.append(f"{words_1_999(millions)} مليون")

    if thousands:
        if thousands == 1:
            parts.append("ألف")
        elif thousands == 2:
            parts.append("ألفان")
        elif 3 <= thousands <= 10:
            parts.append(f"{words_1_999(thousands)} آلاف")
        else:
            parts.append(f"{words_1_999(thousands)} ألف")

    if hundreds_:
        parts.append(words_1_999(hundreds_))

    return " و ".join(parts)
