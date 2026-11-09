"""Small unit tests: settings, formatting, password/session primitives, the frame cache."""

import asyncio
import uuid

import pytest
from app.core import security
from app.core.config import Settings
from app.services.analytics.formatting import Formatters, js_round, to_fixed
from app.services.analytics.frames import FrameCache
from pydantic import ValidationError


# ----------------------------------------------------------------------------------------- settings
class TestSettings:
    @pytest.mark.parametrize(
        "url",
        ["postgres://u:p@h:5432/db", "postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"],
    )
    def test_any_postgres_url_is_normalised_to_the_psycopg_driver(self, url):
        settings = Settings(database_url=url)
        assert settings.database_url == "postgresql+psycopg://u:p@h:5432/db"
        assert settings.psycopg_conninfo == "postgresql://u:p@h:5432/db"

    @pytest.mark.parametrize("url", ["mysql://u:p@h/db", "sqlite:///x.db", "postgresql+asyncpg://u:p@h/db"])
    def test_other_databases_and_drivers_are_refused(self, url):
        with pytest.raises(ValidationError, match="PostgreSQL"):
            Settings(database_url=url)

    def test_cors_origins_accept_a_comma_list_or_json(self):
        assert Settings(cors_origins="http://a.test, http://b.test/").cors_origins == ["http://a.test", "http://b.test"]
        assert Settings(cors_origins='["http://a.test"]').cors_origins == ["http://a.test"]

    def test_wildcard_origin_is_impossible_with_credentials(self):
        with pytest.raises(ValidationError, match="explicit origins"):
            Settings(cors_origins="*")

    def test_samesite_none_requires_secure_cookies(self):
        with pytest.raises(ValidationError, match="requires secure cookies"):
            Settings(cookie_samesite="none", cookie_secure=False)
        assert Settings(cookie_samesite="none", environment="production").effective_cookie_secure is True

    @pytest.mark.parametrize(("raw", "expected"), [("api", "/api"), ("/v1/", "/v1"), ("", ""), ("/", "")])
    def test_api_prefix_is_normalised(self, raw, expected):
        assert Settings(api_prefix=raw).api_prefix == expected


# --------------------------------------------------------------------------------------- formatting
class TestFormatting:
    def test_to_fixed_matches_javascript(self):
        assert [to_fixed(*a) for a in [(0.25, 1), (2.5, 0), (1.005, 2), (1.45, 1), (-3.05, 1), (-0.04, 1), (-0.0, 1), (99.95, 0)]] == [
            "0.3", "3", "1.00", "1.4", "-3.0", "-0.0", "0.0", "100",
        ]  # fmt: skip

    def test_js_round(self):
        assert [js_round(v) for v in (2.5, -2.5, 2.4999, -0.5, 0.5)] == [3, -2, 2, 0, 1]

    @pytest.mark.parametrize(
        ("currency", "locale", "money", "number", "date"),
        [
            ("INR", "en-IN", "₹12,34,568", "12,34,567.8", "15 Aug 2026"),
            ("USD", "en-US", "$1,234,568", "1,234,567.8", "Aug 15, 2026"),
            ("EUR", "de-DE", "1.234.568\xa0€", "1.234.567,8", "15. Aug. 2026"),
            ("GBP", "en-GB", "£1,234,568", "1,234,567.8", "15 Aug 2026"),
        ],
    )
    def test_cldr_formats_match_intl(self, currency, locale, money, number, date):
        import datetime as dt

        f = Formatters.create(currency, locale)
        assert f.currency(1234567.5) == money  # ties go away from zero, like ICU
        assert f.number(1234567.84) == number
        assert f.date(dt.date(2026, 8, 15), "long") == date

    def test_negative_numbers_and_percentages(self):
        f = Formatters.create("INR", "en-IN")
        assert f.currency(-1234.4) == "-₹1,234" and f.number(42) == "42"
        assert [f.percent(v, signed=True) for v in (12.34, -3.05, 0)] == ["+12.3%", "-3.0%", "0.0%"]
        assert f.percent(5) == "5.0%" and f.percent(99.95, digits=0) == "100%"

    def test_unknown_currency_or_locale(self):
        with pytest.raises(ValueError, match="Unknown currency"):
            Formatters.create("XXXX", "en-IN")
        with pytest.raises(ValueError, match="Unknown locale"):
            Formatters.create("INR", "zz-ZZ")


# ---------------------------------------------------------------------------------------- security
class TestSecurity:
    def test_passwords_are_argon2id_and_verify(self):
        hashed = security.hash_password("Passw0rdOK")
        assert hashed.startswith("$argon2id$") and "Passw0rdOK" not in hashed
        assert security.verify_password("Passw0rdOK", hashed)[0] is True
        assert security.verify_password("passw0rdok", hashed)[0] is False
        assert security.hash_password("Passw0rdOK") != hashed  # salted

    def test_weaker_hashes_are_upgraded_on_login(self):
        from pwdlib import PasswordHash
        from pwdlib.hashers.argon2 import Argon2Hasher

        weak = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),)).hash("Passw0rdOK")
        strong = PasswordHash((Argon2Hasher(time_cost=2, memory_cost=2048, parallelism=1),))
        valid, upgraded = strong.verify_and_update("Passw0rdOK", weak)
        assert valid and upgraded and upgraded != weak

    def test_session_tokens(self):
        a, b = security.new_session_token(), security.new_session_token()
        assert a != b and len(a) >= 43  # 256 bits, url-safe
        assert security.hash_token(a) == security.hash_token(a) and security.hash_token(a) != security.hash_token(b)
        assert len(security.hash_token(a)) == 64 and a not in security.hash_token(a)

    def test_dummy_hash_exists_for_constant_time_logins(self):
        assert security.dummy_hash() == security.dummy_hash() and security.dummy_hash().startswith("$argon2")


# --------------------------------------------------------------------------------------- frame cache
class FakeFrame:
    def __init__(self, nbytes):
        self.nbytes = nbytes


class TestFrameCache:
    def test_lru_eviction_by_count(self):
        cache = FrameCache(max_items=2, max_bytes=10**9)
        a, b, c = (uuid.uuid4() for _ in range(3))
        cache.put(a, FakeFrame(1))
        cache.put(b, FakeFrame(1))
        assert cache.get(a)  # touching `a` makes `b` the least recently used
        cache.put(c, FakeFrame(1))
        assert cache.get(b) is None and cache.get(a) and cache.get(c)

    def test_eviction_by_size_always_keeps_the_newest(self):
        cache = FrameCache(max_items=10, max_bytes=100)
        a, b = uuid.uuid4(), uuid.uuid4()
        cache.put(a, FakeFrame(60))
        cache.put(b, FakeFrame(60))
        assert cache.get(a) is None and cache.get(b)
        cache.put(a, FakeFrame(500))  # bigger than the whole budget: still served, everything else is dropped
        assert cache.get(a) and cache.get(b) is None

    def test_evict_and_clear(self):
        cache = FrameCache(2, 10**9)
        key = uuid.uuid4()
        cache.put(key, FakeFrame(1))
        cache.evict(key)
        cache.evict(key)  # idempotent
        assert len(cache) == 0

    async def test_loader_failures_are_not_cached_and_do_not_wedge_the_lock(self):
        cache = FrameCache(2, 10**9)
        key, calls = uuid.uuid4(), 0

        async def flaky():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)
            if calls == 1:
                raise RuntimeError("db hiccup")
            return FakeFrame(1)

        with pytest.raises(RuntimeError):
            await cache.get_or_load(key, flaky)
        assert (await cache.get_or_load(key, flaky)).nbytes == 1 and calls == 2
