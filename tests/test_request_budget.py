import concurrent.futures
import unittest
from unittest.mock import patch

from harnesslab.request_budget import (
    BudgetExhausted, NoRedirect, ProviderFailure, TrialRequestBudget, https_transport,
)


class RequestBudgetTests(unittest.TestCase):
    def test_one_request_then_caller_retry_is_blocked(self):
        calls = []
        boundary = TrialRequestBudget(1, lambda body: calls.append(body) or b"ok")
        self.assertEqual(boundary.send(b"request"), b"ok")
        with self.assertRaises(BudgetExhausted):
            boundary.send(b"request")
        self.assertEqual(calls, [b"request"])
        self.assertEqual(boundary.attempts, 1)

    def test_failures_consume_budget_without_internal_retry(self):
        for error in (TimeoutError(), OSError("429"), OSError("500"), ValueError("bad response")):
            with self.subTest(error=type(error).__name__):
                calls = []
                def fail(body):
                    calls.append(body)
                    raise error
                boundary = TrialRequestBudget(1, fail)
                with self.assertRaises(ProviderFailure):
                    boundary.send(b"private body")
                with self.assertRaises(BudgetExhausted):
                    boundary.send(b"private body")
                self.assertEqual(len(calls), 1)
                self.assertEqual(boundary.audit[0].outcome, "failed")
                self.assertNotIn("private", repr(boundary.audit))

    def test_concurrent_callers_cannot_exceed_limit(self):
        boundary = TrialRequestBudget(3, lambda body: b"ok")
        def attempt(_):
            try:
                boundary.send(b"request")
                return True
            except BudgetExhausted:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            successes = list(pool.map(attempt, range(100)))
        self.assertEqual(sum(successes), 3)
        self.assertEqual(boundary.attempts, 3)
        self.assertEqual([row.number for row in boundary.audit], [1, 2, 3])

    def test_invalid_request_does_not_consume_attempt(self):
        boundary = TrialRequestBudget(1, lambda body: b"ok")
        for value in ("not bytes", b"x" * (1024 * 1024 + 1)):
            with self.assertRaises(ValueError):
                boundary.send(value)
        self.assertEqual(boundary.attempts, 0)

    def test_invalid_limits_rejected(self):
        for value in (True, 0, -1, 1.5):
            with self.assertRaises(ValueError):
                TrialRequestBudget(value, lambda body: body)

    def test_transport_constructor_does_not_connect(self):
        with patch("urllib.request.build_opener") as builder:
            send = https_transport("https://provider.invalid/v1/chat/completions", "fixture")
            self.assertTrue(callable(send))
            builder.return_value.open.assert_not_called()

    def test_transport_failure_is_one_open_and_sanitized(self):
        with patch("urllib.request.build_opener") as builder:
            builder.return_value.open.side_effect = OSError("fixture-secret-response")
            send = https_transport("https://provider.invalid/v1/chat/completions", "fixture")
            with self.assertRaises(ProviderFailure) as caught:
                send(b"{}")
            self.assertEqual(builder.return_value.open.call_count, 1)
            self.assertNotIn("fixture-secret-response", str(caught.exception))

    def test_redirects_are_not_followed(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid"))

    def test_bad_endpoint_rejected(self):
        for url in ("http://provider.invalid", "https://u:p@provider.invalid", "https://provider.invalid?q=x"):
            with self.assertRaises(ValueError):
                https_transport(url, "fixture")


class UsageObservationTests(unittest.TestCase):
    def test_provider_reported_usage_is_captured_without_body(self):
        raw=b'{"usage":{"prompt_tokens":2,"completion_tokens":3,"total_tokens":5},"private":"fixture"}'
        boundary=TrialRequestBudget(1,lambda body:raw)
        boundary.send(b"fixture")
        row=boundary.audit[0]
        self.assertEqual(row.usage_status,"provider_reported")
        self.assertEqual((row.prompt_tokens,row.completion_tokens,row.total_tokens),(2,3,5))
        self.assertNotIn("private",repr(row))

    def test_absent_malformed_and_inconsistent_usage_are_unknown(self):
        for raw in (b'{}', b'bad-json', b'{"usage":{"prompt_tokens":true,"completion_tokens":0,"total_tokens":1}}',
                    b'{"usage":{"prompt_tokens":2,"completion_tokens":3,"total_tokens":9}}'):
            boundary=TrialRequestBudget(1,lambda body:raw)
            boundary.send(b"fixture")
            self.assertEqual(boundary.audit[0].usage_status,"unknown")
            self.assertIsNone(boundary.audit[0].total_tokens)


class SafeFailureDiagnosticsTests(unittest.TestCase):
    def test_http_status_survives_without_private_content_or_retry(self):
        import io
        import urllib.error
        for status in (301,400,401,403,413,429,500,503):
            error=urllib.error.HTTPError('https://private.invalid?secret=value',status,
                'private-reason',{'Private-Header':'private'},io.BytesIO(b'private-response'))
            with patch('urllib.request.build_opener') as builder:
                builder.return_value.open.side_effect=error
                budget=TrialRequestBudget(1,https_transport('https://provider.invalid/endpoint','private-token'))
                with self.assertRaises(ProviderFailure) as caught:budget.send(b'private-request')
                row=budget.audit[0]
                self.assertEqual(row.http_status,status)
                self.assertEqual(row.failure_category,'redirect_refused' if status==301 else 'http_error')
                self.assertEqual(builder.return_value.open.call_count,1)
                self.assertNotIn('private',repr(row)+str(caught.exception))
                with self.assertRaises(BudgetExhausted):budget.send(b'private-request')
                self.assertEqual(builder.return_value.open.call_count,1)

    def test_network_tls_timeout_categories_no_messages(self):
        import ssl
        import urllib.error
        for error,category in [(TimeoutError('private'),'timeout'),
                (urllib.error.URLError(TimeoutError('private')),'timeout'),
                (ssl.SSLError('private'),'tls_error'),
                (urllib.error.URLError(ssl.SSLError('private')),'tls_error'),
                (OSError('private'),'network_error'),
                (ValueError('private'),'unknown_transport_error')]:
            with patch('urllib.request.build_opener') as builder:
                builder.return_value.open.side_effect=error
                budget=TrialRequestBudget(1,https_transport('https://provider.invalid','private-token'))
                with self.assertRaises(ProviderFailure):budget.send(b'private-request')
                self.assertEqual(budget.audit[0].failure_category,category)
                self.assertIsNone(budget.audit[0].http_status)
                self.assertNotIn('private',repr(budget.audit))

    def test_arbitrary_custom_exception_attributes_are_not_logged(self):
        error=RuntimeError('private');error.category='private';error.http_status=123
        def fail(body):raise error
        budget=TrialRequestBudget(1,fail)
        with self.assertRaises(ProviderFailure):budget.send(b'private')
        self.assertEqual(budget.audit[0].failure_category,'unknown_transport_error')
        self.assertIsNone(budget.audit[0].http_status)
        self.assertNotIn('private',repr(budget.audit))

    def test_invalid_transport_result_and_oversized_response(self):
        budget=TrialRequestBudget(1,lambda body:'not bytes private')
        with self.assertRaises(ProviderFailure):budget.send(b'private')
        self.assertEqual(budget.audit[0].failure_category,'invalid_transport_result')
        with patch('urllib.request.build_opener') as builder:
            response=builder.return_value.open.return_value.__enter__.return_value
            response.status=200;response.read.return_value=b'x'*(8*1024*1024+1)
            budget=TrialRequestBudget(1,https_transport('https://provider.invalid','private'))
            with self.assertRaises(ProviderFailure):budget.send(b'private')
            self.assertEqual(budget.audit[0].failure_category,'response_too_large')

    def test_allowlist_constructor_refuses_arbitrary_diagnostics(self):
        for category in ('private', ['private'], {'private':1},None):
            error=ProviderFailure('private',category=category,http_status='private')
            self.assertEqual(error.category,'unknown_transport_error')
            self.assertIsNone(error.http_status)
            self.assertNotIn('private',str(error))
        self.assertIsNone(ProviderFailure(http_status=True).http_status)

    def test_success_has_no_failure_diagnostic(self):
        budget=TrialRequestBudget(1,lambda body:b'{}');budget.send(b'{}')
        self.assertIsNone(budget.audit[0].failure_category)
        self.assertIsNone(budget.audit[0].http_status)
