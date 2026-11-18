import concurrent.futures
import json
import unittest
import urllib.error
import urllib.request

from harnesslab.request_budget import TrialRequestBudget
from harnesslab.trial_gateway import trial_gateway


class TrialGatewayTests(unittest.TestCase):
    def request(self, base, body, path="/chat/completions"):
        request = urllib.request.Request(
            base + path, data=body, method="POST",
            headers={"Content-Type": "application/json", "Authorization": "Bearer fixture-client"},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_loopback_requests_share_trial_budget(self):
        calls = []
        boundary = TrialRequestBudget(1, lambda body: calls.append(body) or b'{"choices": []}')
        with trial_gateway(boundary, expected_model="fixture-model", max_output_tokens=64) as base:
            self.assertEqual(self.request(base, b'{"stream":false,"model":"fixture-model","messages":[{"role":"user","content":"fixture"}]}')[0], 200)
            self.assertEqual(self.request(base, b'{"stream":false,"model":"fixture-model","messages":[{"role":"user","content":"fixture"}]}')[0], 400)
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(calls[0])["max_tokens"], 64)

    def test_provider_failure_is_not_retried(self):
        calls = []
        def fail(body):
            calls.append(body)
            raise TimeoutError("private response fixture")
        boundary = TrialRequestBudget(1, fail)
        with trial_gateway(boundary, expected_model="fixture-model", max_output_tokens=64) as base:
            status, response = self.request(base, b'{"stream":false,"model":"fixture-model","messages":[{"role":"user","content":"fixture"}]}')
            self.assertEqual(status, 502)
            self.assertNotIn("private", str(response))
            self.assertEqual(self.request(base, b'{"stream":false,"model":"fixture-model","messages":[{"role":"user","content":"fixture"}]}')[0], 400)
        self.assertEqual(len(calls), 1)

    def test_invalid_requests_never_reach_upstream(self):
        calls = []
        boundary = TrialRequestBudget(1, lambda body: calls.append(body) or b'{}')
        with trial_gateway(boundary, expected_model="fixture-model", max_output_tokens=64) as base:
            for body in (b'bad-json', b'[]', b'{"stream": true}', b'{}', b'{"stream":false,"model":"other","messages":[{}]}', b'{"stream":false,"model":"fixture-model","messages":[{}],"max_tokens":65}'):
                self.assertEqual(self.request(base, body)[0], 400)
            self.assertEqual(self.request(base, b'{"stream":false,"model":"fixture-model","messages":[{"role":"user","content":"fixture"}]}', '/other')[0], 404)
        self.assertEqual(calls, [])

    def test_malformed_upstream_still_consumes_attempt(self):
        boundary = TrialRequestBudget(1, lambda body: b'bad-json')
        with trial_gateway(boundary, expected_model="fixture-model", max_output_tokens=64) as base:
            self.assertEqual(self.request(base, b'{"stream":false,"model":"fixture-model","messages":[{"role":"user","content":"fixture"}]}')[0], 502)
            self.assertEqual(self.request(base, b'{"stream":false,"model":"fixture-model","messages":[{"role":"user","content":"fixture"}]}')[0], 400)
        self.assertEqual(boundary.attempts, 1)

    def test_concurrent_http_requests_cannot_exceed_budget(self):
        boundary = TrialRequestBudget(2, lambda body: b'{}')
        with trial_gateway(boundary, expected_model="fixture-model", max_output_tokens=64) as base:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                statuses = list(pool.map(lambda _: self.request(base, b'{"stream":false,"model":"fixture-model","messages":[{"role":"user","content":"fixture"}]}')[0], range(10)))
        self.assertEqual(statuses.count(200), 2)
        self.assertEqual(statuses.count(400), 8)
