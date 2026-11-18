"""Canonical request IDs for the Token Codex endpoint only."""

import argparse
import re
import sys
from urllib.parse import urlsplit

ACCEPTED = ("gpt-6.2-sol", "GPT-6.1-terra", "gpt-6.2-astra")


def is_token_codex(base_url):
    url = urlsplit(base_url)
    return (url.scheme == "https" and url.netloc.lower() in
            ("codex.anhlaptrinh.vn", "codex.anhlaptrinh.vn:443")
            and url.path.rstrip("/") == "/v1" and not url.query and not url.fragment)


def token_model(requested):
    if requested is None:
        return ACCEPTED[0]
    alias = re.sub(r"[\s_-]+", "-", requested.strip().lower())
    for model in ACCEPTED:
        if model.lower() == alias:
            return model
    raise ValueError("Token Codex supports: " + ", ".join(ACCEPTED))


def codex_base_url(path):
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            raise SystemExit("Reading Codex TOML requires Python 3.11+ or tomli.")
    with open(path, "rb") as config:
        parsed = tomllib.load(config)
    return parsed.get("model_providers", {}).get(parsed.get("model_provider"), {}).get("base_url", "")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resolve a Token Codex model; print nothing for other providers.")
    parser.add_argument("--codex-config", help="Read the active provider from TOML; otherwise read a URL from stdin")
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    try:
        url = codex_base_url(args.codex_config) if args.codex_config else sys.stdin.readline().strip()
        active = is_token_codex(url)
    except (OSError, AttributeError, TypeError, ValueError):
        parser.error("Cannot determine the active provider URL from configuration.")
    if active:
        try:
            print(token_model(args.model))
        except ValueError as error:
            parser.error(str(error))
