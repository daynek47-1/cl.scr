"""Error code mapping system for consistent error handling and display"""
import re
from typing import Tuple, Optional
import requests.exceptions as req_exc


class ErrorCode:
    """
    Error code definitions with emoji indicators

    1xx: Network & Connection Errors
    2xx: Content & Parsing Errors
    3xx: Logic & Authentication Errors
    4xx-5xx: Standard HTTP Status Codes
    """

    # Network & Connection Errors (1xx)
    E101 = ("E101", "⛔", "Server Down", "The server for the website is not responding.")
    E102 = ("E102", "⛔", "DNS Error", "The domain name could not be resolved.")
    E103 = ("E103", "⛔", "Connection Error", "A generic connection error occurred.")
    E104 = ("E104", "⛔", "Timeout", "The request timed out.")
    E105 = ("E105", "⛔", "HTTP Protocol Error", "A generic HTTP protocol violation occurred.")
    E106 = ("E106", "⛔", "Request Error", "An error occurred while constructing or sending the request.")

    # Content & Parsing Errors (2xx)
    E201 = ("E201", "⛔", "ID/Name Missing", "Could not find merchant ID or name.")
    E202 = ("E202", "⛔", "Captcha/Bot Block", "Access blocked by captcha or bot protection.")

    # Logic & Authentication Errors (3xx)
    E301 = ("E301", "⛔", "Unexpected Error", "An unhandled exception occurred.")
    E302 = ("E302", "⛔", "No Response", "Server returned empty response.")
    E303 = ("E303", "⛔", "Not Modified", "Content has not changed since last request.")
    E304 = ("E304", "⛔", "Login Failed", "Authentication failed for all configured usernames.")
    E305 = ("E305", "⛔", "No Login Data", "Login completed but returned no JSON data.")
    E306 = ("E306", "⛔", "No Bonus Data", "Bonus data endpoint returned empty or invalid response.")

    # HTTP Status Codes (4xx-5xx)
    E403 = ("403", "🛡️", "Forbidden", "Access denied. Geo-block or WAF rule.")
    E404 = ("404", "👻", "Not Found", "The API endpoint or page URL does not exist.")
    E500 = ("500", "⛔", "Internal Server Error", "The remote server crashed.")
    E502 = ("502", "⛔", "Bad Gateway", "Invalid response from upstream server.")
    E503 = ("503", "🚧", "Service Unavailable", "Site under maintenance or overloaded.")


def map_exception_to_error(exception: Exception) -> Tuple[str, str, str, str]:
    """
    Map an exception to an error code

    Returns: (code, emoji, short_desc, long_desc)
    """
    error_str = str(exception).lower()
    exc_type = type(exception).__name__

    # DNS/Name Resolution Errors
    if 'name resolution' in error_str or 'getaddrinfo' in error_str or 'no address associated' in error_str:
        return ErrorCode.E102

    # Connection Errors
    if isinstance(exception, (req_exc.ConnectionError, ConnectionError)):
        if 'max retries' in error_str or 'retry' in error_str:
            return ErrorCode.E101  # Server Down
        return ErrorCode.E103  # Generic connection error

    # Timeout Errors
    if isinstance(exception, (req_exc.Timeout, TimeoutError)) or 'timeout' in error_str:
        return ErrorCode.E104

    # HTTP Errors with status codes
    if isinstance(exception, req_exc.HTTPError):
        if hasattr(exception, 'response') and exception.response is not None:
            status = exception.response.status_code
            if status == 403:
                return ErrorCode.E403
            elif status == 404:
                return ErrorCode.E404
            elif status == 500:
                return ErrorCode.E500
            elif status == 502:
                return ErrorCode.E502
            elif status == 503:
                return ErrorCode.E503
            elif 400 <= status < 500:
                return (str(status), "⛔", f"HTTP {status}", f"Client error {status}")
            elif 500 <= status < 600:
                return (str(status), "⛔", f"HTTP {status}", f"Server error {status}")
        return ErrorCode.E105  # Generic HTTP protocol error

    # Request Errors
    if isinstance(exception, (req_exc.RequestException, req_exc.InvalidURL)):
        return ErrorCode.E106

    # Captcha/Bot Detection
    if 'captcha' in error_str or 'recaptcha' in error_str or 'cloudflare' in error_str:
        return ErrorCode.E202

    # Empty/None Response
    if 'nonetype' in error_str or 'none' in exc_type.lower():
        return ErrorCode.E302

    # Generic fallback
    return ErrorCode.E301


def map_auth_error(error_type: str, exception: Optional[Exception] = None) -> Tuple[str, str, str, str]:
    """
    Map authentication-specific errors to error codes

    Args:
        error_type: 'no_merchant_id', 'login_failed', 'no_login_data', 'exception'
        exception: Optional exception object

    Returns: (code, emoji, short_desc, long_desc)
    """
    if error_type == 'no_merchant_id':
        return ErrorCode.E201
    elif error_type == 'login_failed':
        return ErrorCode.E304
    elif error_type == 'no_login_data':
        return ErrorCode.E305
    elif error_type == 'exception' and exception:
        return map_exception_to_error(exception)
    else:
        return ErrorCode.E301


def map_api_error(error_type: str, exception: Optional[Exception] = None) -> Tuple[str, str, str, str]:
    """
    Map API-specific errors to error codes

    Args:
        error_type: 'no_session', 'no_bonus_data', 'exception'
        exception: Optional exception object

    Returns: (code, emoji, short_desc, long_desc)
    """
    if error_type == 'no_session':
        return ErrorCode.E304  # Auth failed
    elif error_type == 'no_bonus_data':
        return ErrorCode.E306
    elif error_type == 'exception' and exception:
        return map_exception_to_error(exception)
    else:
        return ErrorCode.E301


def format_error_for_display(code: str, emoji: str, short_desc: str, verbosity: str = 'min') -> str:
    """
    Format error for display based on verbosity level

    Args:
        code: Error code (e.g., "E101", "403")
        emoji: Emoji indicator
        short_desc: Short description
        verbosity: 'min', 'med', or 'max'

    Returns: Formatted string for display
    """
    if verbosity == 'min':
        return f"{emoji}E{code}"
    elif verbosity == 'med':
        return f"{emoji}{short_desc}"
    else:  # max
        return f"{emoji}E{code}: {short_desc}"
