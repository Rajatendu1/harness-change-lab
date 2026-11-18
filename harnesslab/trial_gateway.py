"""Loopback-only JSON gateway for the prepare-only request budget prototype.

Not a sandbox. The parent controller must keep real credentials out of the agent
process and prevent alternate provider routes. Streaming is deliberately refused.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import socketserver
import os
from pathlib import Path
import stat

from .request_budget import BudgetExhausted, ProviderFailure


@contextmanager
def trial_gateway(budget, *, expected_model, max_output_tokens, unix_path=None, shared_group=None,
                  request_policy=None, token_counter=None):
    if not expected_model or type(max_output_tokens) is not int or max_output_tokens <= 0:
        raise ValueError("Expected a fixed model and positive output-token cap")
    if (request_policy is None) != (token_counter is None):
        raise ValueError('Admission policy and reviewed tokenizer are required together')
    if request_policy is not None:
        from .request_admission import TextRequestPolicy
        if (not isinstance(request_policy, TextRequestPolicy) or not callable(token_counter)
                or request_policy.model != expected_model
                or request_policy.max_output_tokens != max_output_tokens):
            raise ValueError('Admission identity and output bound must match gateway')
    group_directory = None
    original_directory_mode = None
    if shared_group is not None:
        if (not unix_path or type(shared_group) is not int or shared_group != os.getgid()
                or shared_group <= 0):
            raise ValueError('Shared gateway requires the controller nonroot primary group')
        group_directory = Path(unix_path).parent
        metadata = group_directory.lstat()
        if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_gid != shared_group or stat.S_IMODE(metadata.st_mode) != 0o700
                or list(group_directory.iterdir())):
            raise ValueError('Shared gateway requires an empty private socket-only directory')
        original_directory_mode = stat.S_IMODE(metadata.st_mode)
    allowed_keys = {"model", "messages", "stream", "temperature", "top_p", "max_tokens", "stop", "seed"}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # No bodies, auth headers or URLs in request logs.

        def reply(self, status, payload):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self.reply(404, {"error": "Unknown endpoint"})
                return
            try:
                if self.headers.get("Transfer-Encoding"):
                    raise ValueError()
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= length <= 1024 * 1024:
                    raise ValueError()
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError()
                payload = json.loads(body)
                if not isinstance(payload, dict) or payload.get("stream", False) is not False:
                    raise ValueError()
                if set(payload) - allowed_keys or payload.get("model") != expected_model:
                    raise ValueError()
                if not isinstance(payload.get("messages"), list) or not payload["messages"]:
                    raise ValueError()
                output_cap = payload.get("max_tokens", max_output_tokens)
                if type(output_cap) is not int or not 0 < output_cap <= max_output_tokens:
                    raise ValueError()
                payload["max_tokens"] = output_cap
                if request_policy is not None:
                    body = request_policy.admit(payload, count_tokens=token_counter)
                else:
                    body = json.dumps(payload, separators=(",", ":")).encode()
            except (ValueError, UnicodeDecodeError):
                self.reply(400, {"error": "Expected bounded non-streaming JSON request"})
                return
            try:
                raw = budget.send(body)
                response = json.loads(raw)
                if not isinstance(response, dict):
                    raise ValueError()
            except BudgetExhausted:
                self.reply(400, {"error": {"code": "trial_budget_exhausted", "message": "Trial request budget exhausted; terminal"}})
                return
            except (ProviderFailure, ValueError, UnicodeDecodeError):
                self.reply(502, {"error": "Provider attempt failed; not retried"})
                return
            self.reply(200, response)

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

    if unix_path:
        class UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
            daemon_threads = True
        server = UnixServer(unix_path, Handler)
        os.chmod(unix_path, 0o660 if shared_group is not None else 0o600)
        if group_directory is not None:
            os.chmod(group_directory, 0o750)
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield unix_path if unix_path else "http://127.0.0.1:%d/v1" % server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=6)
        if group_directory is not None:
            os.chmod(group_directory, original_directory_mode)
