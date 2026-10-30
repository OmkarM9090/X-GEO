"""URL validation + normalisation (``app.core.security``)."""

from __future__ import annotations

import pytest

from app.core.exceptions import InvalidInputError
from app.core.security import MAX_URL_LENGTH, validate_domain, validate_url


class TestValidateUrlHappyPath:
    def test_keeps_https_urls(self) -> None:
        assert validate_url("https://example.com") == "https://example.com"

    def test_keeps_http_urls_with_path(self) -> None:
        assert validate_url("http://example.com/page") == "http://example.com/page"

    def test_strips_trailing_slash(self) -> None:
        assert validate_url("https://example.com/") == "https://example.com"

    def test_lowercases_scheme_and_host(self) -> None:
        assert validate_url("HTTPS://EXAMPLE.com/Path") == "https://example.com/Path"

    def test_preserves_query_string(self) -> None:
        assert validate_url("https://example.com/search?q=geo&page=2") == (
            "https://example.com/search?q=geo&page=2"
        )

    def test_drops_default_ports(self) -> None:
        assert validate_url("https://example.com:443/") == "https://example.com"
        assert validate_url("http://example.com:80/") == "http://example.com"

    def test_keeps_non_default_port(self) -> None:
        assert validate_url("https://example.com:8443/api") == "https://example.com:8443/api"

    def test_accepts_ip_literal(self) -> None:
        assert validate_url("http://93.184.216.34/page") == "http://93.184.216.34/page"

    def test_converts_idn_hosts_to_punycode(self) -> None:
        assert validate_url("https://münchen.de/") == "https://xn--mnchen-3ya.de"

    def test_trims_surrounding_whitespace(self) -> None:
        assert validate_url("  https://example.com  ") == "https://example.com"

    def test_accepts_subdomains_and_hyphens(self) -> None:
        url = "https://blog.staging-1.example.co.uk/post"
        assert validate_url(url) == url


class TestValidateUrlRejections:
    def test_rejects_missing_scheme(self) -> None:
        with pytest.raises(InvalidInputError):
            validate_url("example.com")

    def test_rejects_javascript_scheme(self) -> None:
        with pytest.raises(InvalidInputError, match="Unsupported URL scheme"):
            validate_url("javascript:alert(1)")

    def test_rejects_ftp(self) -> None:
        with pytest.raises(InvalidInputError, match="Unsupported URL scheme"):
            validate_url("ftp://example.com")

    def test_rejects_file_scheme(self) -> None:
        with pytest.raises(InvalidInputError, match="Unsupported URL scheme"):
            validate_url("file:///etc/passwd")

    def test_rejects_empty_and_blank(self) -> None:
        with pytest.raises(InvalidInputError):
            validate_url("")
        with pytest.raises(InvalidInputError):
            validate_url("   ")

    def test_rejects_embedded_whitespace(self) -> None:
        with pytest.raises(InvalidInputError, match="whitespace"):
            validate_url("https://exa mple.com/path")

    def test_rejects_embedded_nul(self) -> None:
        # A NUL byte must never be able to smuggle a second origin past validation.
        with pytest.raises(InvalidInputError, match="control characters"):
            validate_url("https://example.com/\x00http://evil.internal")

    def test_rejects_unsupported_scheme_without_slashes(self) -> None:
        with pytest.raises(InvalidInputError, match="Unsupported URL scheme"):
            validate_url("mailto:someone@example.com")

    def test_rejects_newline_smuggling(self) -> None:
        with pytest.raises(InvalidInputError, match="whitespace"):
            validate_url("https://example.com/\nhttp://evil.internal")

    def test_rejects_single_label_hosts(self) -> None:
        with pytest.raises(InvalidInputError, match="fully qualified"):
            validate_url("http://intranet/wiki")

    def test_allows_single_label_host_when_explicitly_permitted(self) -> None:
        assert (
            validate_url("http://intranet/wiki", allow_private_hosts=True) == "http://intranet/wiki"
        )

    def test_rejects_urls_without_host(self) -> None:
        with pytest.raises(InvalidInputError):
            validate_url("https:///path")

    def test_rejects_overlong_urls(self) -> None:
        with pytest.raises(InvalidInputError, match="maximum length"):
            validate_url("https://example.com/" + "a" * MAX_URL_LENGTH)

    def test_rejects_invalid_port(self) -> None:
        with pytest.raises(InvalidInputError):
            validate_url("https://example.com:notaport/")


class TestValidateDomain:
    def test_returns_origin(self) -> None:
        assert validate_domain("https://example.com/pricing?plan=pro") == "https://example.com"

    def test_keeps_explicit_port(self) -> None:
        assert validate_domain("http://example.com:8080/x") == "http://example.com:8080"

    def test_strips_credentials(self) -> None:
        assert validate_domain("https://user:pass@example.com/private") == "https://example.com"

    def test_propagates_validation_errors(self) -> None:
        with pytest.raises(InvalidInputError):
            validate_domain("not-a-url")
