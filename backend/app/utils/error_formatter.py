"""
utils/error_formatter.py

Formatter to translate raw connector error codes and messages into
clean, human-readable explanations for analysts.
"""

from __future__ import annotations


def format_human_error(error_msg: str | None, error_code: str | int | None = None) -> str | None:
    """
    Format raw error strings/codes into human-readable messages.

    Examples:
    - 401 / "api_key_missing" -> "401: Invalid API Key or Unauthorized Access"
    - 403 -> "403: Access Forbidden (Rate Limit Exceeded or Token Lacks Scope)"
    - 429 -> "429: API Quota Depleted (Rate Limit Reached)"
    - 404 -> "404: Target Not Found in Provider Index"
    - 503 -> "503: Provider Service Temporarily Down"
    - "timeout" -> "Timeout: Provider API did not respond within 10s"
    """
    if not error_msg and not error_code:
        return None

    code_str = str(error_code or "").strip()
    msg_str = str(error_msg or "").strip()

    # Priority check based on status code or string patterns
    if code_str == "401" or "401" in msg_str or code_str == "api_key_missing" or "api key missing" in msg_str.lower() or "unauthorized" in msg_str.lower():
        return "401: Invalid API Key or Unauthorized Access"
    if code_str == "403" or "403" in msg_str or "forbidden" in msg_str.lower():
        return "403: Access Forbidden (Rate Limit Exceeded or Token Lacks Scope)"
    if code_str == "429" or "429" in msg_str or "rate limit" in msg_str.lower() or "quota" in msg_str.lower():
        return "429: API Quota Depleted (Rate Limit Reached)"
    if code_str == "404" or "404" in msg_str or "not found" in msg_str.lower():
        return "404: Target Not Found in Provider Index"
    if code_str in ("500", "502", "503", "504") or "500" in msg_str or "503" in msg_str or "unavailable" in msg_str.lower():
        return "503: External Provider Service Down / Maintenance"
    if code_str == "timeout" or "timeout" in msg_str.lower():
        return "Timeout: Provider API did not respond within deadline"
    if code_str == "validation_error" or "validation" in msg_str.lower():
        return "Validation Error: Invalid target format for connector"
    if code_str == "non_github_domain" or "non-github" in msg_str.lower():
        return "Skipped: Target email domain is not @github.com"
    if code_str == "private_ip":
        return "Skipped: Private / Loopback IP address cannot be queried"

    if msg_str and not msg_str.startswith("HTTP "):
        return msg_str

    if code_str:
        return f"HTTP {code_str}: Provider API Error"

    return "Execution Failed"
