"""Prepare-only provider boundary. No integration with the historical M8 runner.

The controller owns this object for one trial and supplies the fixed upstream
transport. Caller retries consume the same budget, including failed attempts.
No prompt, response body, header, credential or URL is included in the audit.
"""
from dataclasses import dataclass
import json
from threading import Lock
from typing import Callable
import socket
import ssl
import urllib.error
import urllib.request


class BudgetExhausted(RuntimeError):
    pass


FAILURE_CATEGORIES = frozenset({
    'http_error', 'redirect_refused', 'timeout', 'tls_error', 'network_error',
    'response_too_large', 'invalid_transport_result', 'unknown_transport_error',
})


class ProviderFailure(RuntimeError):
    """Only allowlisted metadata survives. No exception/body text is retained."""
    def __init__(self, message='Provider attempt failed; not retried', *, category=None, http_status=None):
        self.category = category if type(category) is str and category in FAILURE_CATEGORIES else 'unknown_transport_error'
        self.http_status = http_status if type(http_status) is int and 100 <= http_status <= 599 else None
        super().__init__('Provider attempt failed; not retried')


def failure_observation(error):
    if isinstance(error, ProviderFailure):
        safe=ProviderFailure(category=error.category,http_status=error.http_status)
        return dict(failure_category=safe.category,http_status=safe.http_status)
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, (TimeoutError, socket.timeout)):
        category = 'timeout'
    elif isinstance(reason, ssl.SSLError):
        category = 'tls_error'
    elif isinstance(reason, OSError):
        category = 'network_error'
    else:
        category = 'unknown_transport_error'
    return dict(failure_category=category, http_status=None)


@dataclass(frozen=True)
class Attempt:
    number: int
    outcome: str
    usage_status: str = "unknown"
    prompt_tokens: object = None
    completion_tokens: object = None
    total_tokens: object = None
    failure_category: object = None
    http_status: object = None


def usage_observation(raw):
    try:
        usage = json.loads(raw)["usage"]
        values = [usage[name] for name in ("prompt_tokens", "completion_tokens", "total_tokens")]
        if any(type(value) is not int or value < 0 for value in values):
            return {}
        if values[2] != values[0] + values[1]:
            return {}
        return dict(usage_status="provider_reported", prompt_tokens=values[0],
                    completion_tokens=values[1], total_tokens=values[2])
    except (ValueError, TypeError, KeyError):
        return {}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def https_transport(url: str, token: str, timeout: float = 60):
    """Return a single-attempt transport. No redirects or retry handler.

    This is not a quota or payment verifier. Construction performs no IO.
    The controller must verify the route and grant before ever invoking it.
    """
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.fragment or parsed.query):
        raise ValueError("Expected a fixed HTTPS endpoint without embedded credentials or query")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    opener = urllib.request.build_opener(NoRedirect())

    def send(body: bytes) -> bytes:
        request = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
            method="POST",
        )
        try:
            with opener.open(request, timeout=timeout) as response:
                if response.status != 200:
                    raise ProviderFailure(category='http_error', http_status=response.status)
                data = response.read(8 * 1024 * 1024 + 1)
                if len(data) > 8 * 1024 * 1024:
                    raise ProviderFailure(category='response_too_large')
                return data
        except urllib.error.HTTPError as error:
            status = error.code if type(error.code) is int else None
            category = 'redirect_refused' if status is not None and 300 <= status <= 399 else 'http_error'
            error.close()
            raise ProviderFailure(category=category, http_status=status) from None
        except ProviderFailure:
            raise
        except Exception as error:
            observation = failure_observation(error)
            raise ProviderFailure(category=observation['failure_category']) from None
    return send


class TrialRequestBudget:
    """Process-local trial scope; never construct a new instance for a retry."""
    def __init__(self, limit: int, transport: Callable[[bytes], bytes]):
        if type(limit) is not int or limit <= 0:
            raise ValueError("limit must be a positive integer")
        self.limit = limit
        self._transport = transport
        self._lock = Lock()
        self._attempts = 0
        self._audit = []

    @property
    def attempts(self):
        with self._lock:
            return self._attempts

    @property
    def audit(self):
        with self._lock:
            return tuple(sorted(self._audit, key=lambda row: row.number))

    def send(self, body: bytes) -> bytes:
        if not isinstance(body, bytes) or len(body) > 1024 * 1024:
            raise ValueError("Expected a bounded byte request")
        with self._lock:
            if self._attempts >= self.limit:
                raise BudgetExhausted("Trial provider-request budget exhausted")
            self._attempts += 1
            number = self._attempts
        try:
            result = self._transport(body)
            if not isinstance(result, bytes):
                raise ProviderFailure(category='invalid_transport_result')
        except Exception as error:
            observation = failure_observation(error)
            with self._lock:
                self._audit.append(Attempt(number, 'failed', **observation))
            raise ProviderFailure(category=observation['failure_category'],
                                  http_status=observation['http_status']) from None
        with self._lock:
            self._audit.append(Attempt(number, "returned", **usage_observation(result)))
        return result
