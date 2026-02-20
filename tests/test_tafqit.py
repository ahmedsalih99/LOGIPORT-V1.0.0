"""
tests/test_tafqit.py
====================
Covers tafqit_service.py — all public functions, all branches.

Functions under test:
  tafqit()             - main API
  number_to_words_ar() - Arabic word conversion
  number_to_words_en() - English word conversion
  number_to_words_tr() - Turkish word conversion
  currency_names()     - currency lookup
"""
import pytest
from services.tafqit_service import (
    tafqit,
    currency_names,
    number_to_words_ar,
    number_to_words_en,
    number_to_words_tr,
)


# ══════════════════════════════════════════════════════════════════════════════
# tafqit()
# ══════════════════════════════════════════════════════════════════════════════

class TestTafqit:

    # ── Arabic ────────────────────────────────────────────────────────────────

    def test_ar_usd_with_cents(self):
        r = tafqit(1234.56, "USD", "ar")
        assert "ألف" in r
        assert "دولار أمريكي" in r
        assert "سنت" in r

    def test_ar_round_no_cents(self):
        r = tafqit(1000.00, "USD", "ar")
        assert "سنت" not in r
        assert "دولار" in r

    def test_ar_zero(self):
        r = tafqit(0.0, "USD", "ar")
        assert "صفر" in r
        assert "دولار" in r

    def test_ar_cents_only(self):
        r = tafqit(0.50, "USD", "ar")
        assert "سنت" in r

    def test_ar_one(self):
        r = tafqit(1.0, "SAR", "ar")
        assert "ريال" in r

    def test_ar_million(self):
        r = tafqit(2_000_000.0, "USD", "ar")
        assert "مليون" in r

    def test_ar_two_thousand(self):
        r = tafqit(2000.0, "USD", "ar")
        assert "ألفان" in r

    # ── English ───────────────────────────────────────────────────────────────

    def test_en_gbp_with_pence(self):
        r = tafqit(5678.90, "GBP", "en")
        assert "five thousand" in r.lower()
        assert "pounds sterling" in r.lower()
        assert "pence" in r.lower()

    def test_en_round_no_cents(self):
        r = tafqit(100.00, "USD", "en")
        assert "cents" not in r.lower()
        assert "hundred" in r.lower()

    def test_en_one_cent(self):
        r = tafqit(0.01, "USD", "en")
        assert "cent" in r.lower()

    def test_en_zero(self):
        r = tafqit(0.0, "USD", "en")
        assert "zero" in r.lower()

    def test_en_million(self):
        r = tafqit(1_000_000.0, "USD", "en")
        assert "million" in r.lower()

    # ── Turkish ───────────────────────────────────────────────────────────────

    def test_tr_try_with_kurus(self):
        r = tafqit(9876.54, "TRY", "tr")
        assert "dokuz bin" in r.lower()
        assert "lira" in r.lower()
        assert "kuruş" in r.lower()

    def test_tr_round_no_kurus(self):
        r = tafqit(500.00, "TRY", "tr")
        assert "kuruş" not in r.lower()

    def test_tr_zero(self):
        r = tafqit(0.0, "TRY", "tr")
        assert "sıfır" in r.lower()

    def test_tr_one_kurus(self):
        r = tafqit(0.01, "TRY", "tr")
        assert "kuruş" in r.lower()

    # ── All known currencies, all languages — no crash ────────────────────────

    @pytest.mark.parametrize("code", [
        "USD", "EUR", "TRY", "GBP", "SAR", "AED",
        "RUB", "CNY", "JPY", "IQD", "EGP", "JOD",
        "KWD", "OMR", "BHD", "QAR",
    ])
    @pytest.mark.parametrize("lang", ["ar", "en", "tr"])
    def test_all_currencies_no_crash(self, code, lang):
        r = tafqit(1234.56, code, lang)
        assert isinstance(r, str) and len(r) > 0

    def test_unknown_currency_no_crash(self):
        r = tafqit(100.0, "XYZ", "en")
        assert isinstance(r, str)

    def test_none_amount_treated_as_zero(self):
        r = tafqit(None, "USD", "en")  # type: ignore
        assert "zero" in r.lower()


# ══════════════════════════════════════════════════════════════════════════════
# number_to_words_ar()
# ══════════════════════════════════════════════════════════════════════════════

class TestNumberToWordsAr:

    @pytest.mark.parametrize("n,expected", [
        (0,         "صفر"),
        (1,         "واحد"),
        (10,        "عشرة"),
        (11,        "أحد عشر"),
        (20,        "عشرون"),
        (21,        "واحد"),    # "واحد و عشرون"
        (100,       "مئة"),
        (200,       "مئتان"),
        (999,       "تسعمئة"),
        (1000,      "ألف"),
        (2000,      "ألفان"),
        (3000,      "آلاف"),   # "ثلاثة آلاف"
        (11000,     "ألف"),    # "أحد عشر ألف"
        (1_000_000, "مليون"),
        (2_000_000, "مليونان"),
        (3_000_000, "ملايين"),
    ])
    def test_key_values(self, n, expected):
        assert expected in number_to_words_ar(n)

    def test_compound_1999(self):
        r = number_to_words_ar(1999)
        assert "ألف" in r
        assert "تسعمئة" in r


# ══════════════════════════════════════════════════════════════════════════════
# number_to_words_en()
# ══════════════════════════════════════════════════════════════════════════════

class TestNumberToWordsEn:

    @pytest.mark.parametrize("n,expected", [
        (0,          "zero"),
        (1,          "one"),
        (13,         "thirteen"),
        (20,         "twenty"),
        (21,         "twenty one"),
        (100,        "one hundred"),
        (115,        "one hundred"),
        (1000,       "one thousand"),
        (1001,       "one thousand"),
        (1_000_000,  "one million"),
        (1_000_000_000, "one billion"),
    ])
    def test_key_values(self, n, expected):
        assert expected in number_to_words_en(n).lower()

    def test_999(self):
        r = number_to_words_en(999).lower()
        assert "nine hundred" in r
        assert "ninety" in r
        assert "nine" in r


# ══════════════════════════════════════════════════════════════════════════════
# number_to_words_tr()
# ══════════════════════════════════════════════════════════════════════════════

class TestNumberToWordsTr:

    @pytest.mark.parametrize("n,expected", [
        (0,         "sıfır"),
        (1,         "bir"),
        (10,        "on"),
        (11,        "on bir"),
        (100,       "yüz"),
        (200,       "iki yüz"),
        (1000,      "bin"),
        (2000,      "iki bin"),
        (1_000_000, "bir milyon"),
    ])
    def test_key_values(self, n, expected):
        assert expected in number_to_words_tr(n).lower()

    def test_1000_is_just_bin_not_bir_bin(self):
        """Turkish: 1000 = 'bin', NOT 'bir bin'."""
        r = number_to_words_tr(1000).lower()
        assert r == "bin"


# ══════════════════════════════════════════════════════════════════════════════
# currency_names()
# ══════════════════════════════════════════════════════════════════════════════

class TestCurrencyNames:

    @pytest.mark.parametrize("code,lang,main_contains,frac_contains", [
        ("USD", "ar", "دولار",   "سنت"),
        ("USD", "en", "dollar",  "cent"),
        ("USD", "tr", "dolar",   "sent"),
        ("TRY", "tr", "lira",    "kuruş"),
        ("GBP", "en", "pound",   "pence"),
        ("SAR", "ar", "ريال",    "هللة"),
        ("IQD", "ar", "دينار",  "فلس"),
    ])
    def test_known_currencies(self, code, lang, main_contains, frac_contains):
        main, frac = currency_names(code, lang)
        assert main_contains.lower() in main.lower()
        assert frac_contains.lower() in frac.lower()

    def test_unknown_code_returns_tuple(self):
        result = currency_names("XYZ", "en")
        assert isinstance(result, tuple) and len(result) == 2

    def test_unknown_code_arabic_fallback(self):
        main, frac = currency_names("ZZZ", "ar")
        assert main  # not empty

    def test_empty_code(self):
        result = currency_names("", "en")
        assert isinstance(result, tuple)

    def test_lowercase_code_normalised(self):
        """currency_names normalises code to upper — 'usd' == 'USD'."""
        r1 = currency_names("usd", "en")
        r2 = currency_names("USD", "en")
        assert r1 == r2