"""SSRF prevention: private ranges, allowlists, DNS failures."""

from __future__ import annotations

import socket

import pytest

from app.config import get_settings
from app.core.exceptions import InvalidInputError, SSRFBlockedError
from app.core.security import build_url_policy, check_ssrf, is_url_safe, resolve_target


class TestPrivateRangesAreBlocked:
    def test_blocks_localhost(self) -> None:
        # Single-label hosts never resolve out of the public DNS namespace, so
        # they are rejected before an address is ever contacted.
        with pytest.raises(ValueError, match="fully qualified"):
            check_ssrf("http://localhost:5432")

    def test_blocks_127_range(self) -> None:
        with pytest.raises(ValueError, match="SSRF blocked"):
            check_ssrf("http://127.0.0.1:8080")

    def test_blocks_private_10(self) -> None:
        with pytest.raises(ValueError, match="SSRF blocked"):
            check_ssrf("http://10.0.0.1/admin")

    def test_blocks_private_172(self) -> None:
        with pytest.raises(ValueError, match="SSRF blocked"):
            check_ssrf("http://172.16.0.1/secret")

    def test_blocks_private_192(self) -> None:
        with pytest.raises(ValueError, match="SSRF blocked"):
            check_ssrf("http://192.168.1.1/api")

    def test_blocks_aws_metadata(self) -> None:
        with pytest.raises(ValueError, match="SSRF blocked"):
            check_ssrf("http://169.254.169.254/latest/meta-data")

    def test_blocks_ipv6_loopback(self) -> None:
        with pytest.raises(ValueError, match="SSRF blocked"):
            check_ssrf("http://[::1]:8000/")

    def test_blocks_cgnat_range(self) -> None:
        with pytest.raises(ValueError, match="SSRF blocked"):
            check_ssrf("http://100.64.12.9/")

    def test_blocks_zero_and_multicast(self) -> None:
        with pytest.raises(ValueError):
            check_ssrf("http://0.0.0.0/")
        with pytest.raises(ValueError):
            check_ssrf("http://224.0.0.1/")

    def test_returns_vetted_target(self) -> None:
        """A public IP literal is returned with its address pinned."""
        target = resolve_target("http://93.184.216.34/page")
        assert target.hostname == "93.184.216.34"
        assert target.primary_ip == "93.184.216.34"
        assert target.host_header == "93.184.216.34"


class TestPublicTargets:
    def test_allows_public_ip_literal(self) -> None:
        check_ssrf("https://93.184.216.34")

    def test_allows_real_domain(self, dns_available: bool) -> None:
        if not dns_available:
            pytest.skip("outbound DNS unavailable")
        check_ssrf("https://example.com")

    def test_is_url_safe_helper(self) -> None:
        assert is_url_safe("https://93.184.216.34") is True
        assert is_url_safe("http://127.0.0.1") is False

    def test_unresolvable_host_is_rejected(self) -> None:
        with pytest.raises(InvalidInputError, match="DNS resolution failed"):
            check_ssrf("https://this-domain-does-not-exist-xgeo.invalid")


class TestAllowlist:
    def test_allowlisted_host_bypasses_block(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "SSRF_ALLOWLIST", ["127.0.0.1"], raising=False)
        target = check_ssrf("http://127.0.0.1:9000/health")
        assert target.primary_ip == "127.0.0.1"

    def test_allowlisted_cidr_bypasses_block(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "SSRF_ALLOWLIST", ["10.0.0.0/8"], raising=False)
        check_ssrf("http://10.1.2.3/internal")

    def test_suffix_match_for_allowlisted_domain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "SSRF_ALLOWLIST", ["localhost"], raising=False)
        target = check_ssrf("http://localhost:5432")
        assert target.primary_ip in {"127.0.0.1", "::1"}

    def test_allowlist_does_not_leak_to_other_hosts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "SSRF_ALLOWLIST", ["10.0.0.0/8"], raising=False)
        with pytest.raises(ValueError, match="SSRF blocked"):
            check_ssrf("http://192.168.1.1/")


class TestPolicyConstruction:
    def test_policy_includes_configured_ranges(self) -> None:
        policy = build_url_policy()
        assert policy.blocked_networks
        assert policy.strict_mode is True

    def test_invalid_range_is_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = get_settings()
        monkeypatch.setattr(
            settings, "SSRF_BLOCKED_RANGES", ["not-a-cidr", "127.0.0.0/8"], raising=False
        )
        policy = build_url_policy()
        assert len(policy.blocked_networks) == 1

    def test_dns_failure_raises_invalid_input(self) -> None:
        with pytest.raises(InvalidInputError):
            resolve_target("https://nonexistent-host-for-xgeo-tests.invalid")


class TestDnsRebindingDefence:
    def test_all_resolved_addresses_are_checked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A host resolving to a public *and* a private address must be blocked."""

        def fake_getaddrinfo(host: str, port: int, **kwargs: object):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port or 0)),
            ]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(SSRFBlockedError, match="SSRF blocked"):
            check_ssrf("https://rebinding.example.com/")
