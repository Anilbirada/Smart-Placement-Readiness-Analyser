from __future__ import annotations

import ipaddress
import re
from typing import Any, Dict
from urllib.parse import parse_qs, urlsplit


MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = {"http", "https"}


def normalize_url_for_analysis(raw_url: str) -> str:
    if raw_url is None:
        raise ValueError("URL value is missing.")

    candidate = raw_url.strip()
    if not candidate:
        raise ValueError("URL must not be empty.")

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidate):
        candidate = "https://" + candidate.lstrip("/")

    if len(candidate) > MAX_URL_LENGTH:
        raise ValueError("URL is too long for analysis.")

    try:
        split = urlsplit(candidate)
    except ValueError as exc:
        raise ValueError("The URL is malformed and cannot be analysed.") from exc

    scheme = (split.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only HTTP and HTTPS URLs are supported for analysis.")

    if not split.hostname:
        raise ValueError("The URL does not include a valid hostname.")

    return candidate


def _coerce_hostname(hostname: str) -> str:
    if not hostname:
        return ""
    return hostname.strip().rstrip(".")


def extract_url_features(raw_url: str) -> Dict[str, Any]:
    candidate = normalize_url_for_analysis(raw_url)

    scheme_match = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*)://", candidate)
    if not scheme_match:
        raise ValueError("The URL is missing a valid scheme such as http:// or https://")

    scheme = scheme_match.group(1).lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only HTTP and HTTPS URLs are supported for analysis.")

    split = urlsplit(candidate)
    hostname = _coerce_hostname(split.hostname or "")
    if not hostname:
        raise ValueError("The URL does not include a valid hostname.")

    try:
        ipaddress.ip_address(hostname)
        is_ip_address = True
    except ValueError:
        is_ip_address = False

    path = split.path or ""
    query = split.query or ""
    netloc = split.netloc or ""

    hostname_for_count = hostname
    number_of_dots = hostname_for_count.count(".")
    number_of_hyphens = hostname_for_count.count("-")
    number_of_digits = sum(ch.isdigit() for ch in hostname_for_count)
    number_of_parameters = len(parse_qs(query, keep_blank_values=True)) if query else 0
    has_at_sign = "@" in netloc
    punycode_indicator = hostname_for_count.startswith("xn--")
    suspicious_encoding_pattern = bool(re.search(r"(%[0-9A-Fa-f]{2}|%25)", candidate))

    unusual_hostname_pattern = bool(
        re.search(r"(?:[-_]{2,}|\d{3,}|[A-Za-z]{20,})", hostname_for_count)
    ) or hostname_for_count.count("-") > 3

    if hostname_for_count.startswith("www."):
        hostname_without_www = hostname_for_count[4:]
    else:
        hostname_without_www = hostname_for_count
    subdomains = hostname_without_www.split(".") if hostname_without_www else []
    number_of_subdomains = max(0, len(subdomains) - 1) if not is_ip_address else 0

    features = {
        "total_url_length": len(candidate),
        "hostname_length": len(hostname_for_count),
        "path_length": len(path),
        "number_of_dots": number_of_dots,
        "number_of_hyphens": number_of_hyphens,
        "number_of_digits": number_of_digits,
        "number_of_parameters": number_of_parameters,
        "is_ip_address": is_ip_address,
        "has_at_sign": has_at_sign,
        "scheme": scheme,
        "punycode_indicator": punycode_indicator,
        "unusual_hostname_pattern": unusual_hostname_pattern,
        "number_of_subdomains": number_of_subdomains,
        "suspicious_encoding_pattern": suspicious_encoding_pattern,
    }
    return features
