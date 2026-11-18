"""Read-only bootstrap inside a fresh network/PID/mount namespace.

Only this loopback HTTP bridge can reach the mounted controller Unix socket.
The child has no provider token. No request/response data is logged here.
"""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
import resource
import subprocess
import sys
from threading import Thread


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Longer than the fixed transport default (60s); outer trial timeout wins.
        self.sock.settimeout(65)
        self.sock.connect('/gateway/provider.sock')


class Bridge(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if self.headers.get('Transfer-Encoding') or not 0 <= length <= 1024 * 1024:
                raise ValueError()
            if self.path != '/v1/chat/completions':
                raise ValueError()
            body = self.rfile.read(length)
            connection = UnixConnection('localhost')
            try:
                connection.request('POST', self.path, body, {'Content-Type': 'application/json'})
                response = connection.getresponse()
                data = response.read(8 * 1024 * 1024 + 1)
                if len(data) > 8 * 1024 * 1024:
                    raise ValueError()
                status = response.status
            finally:
                connection.close()
        except Exception:
            status, data = 400, b'{"error":"Bridge request rejected"}'
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def setup(self):
        super().setup()
        self.connection.settimeout(10)


if __name__ == '__main__':
    command = json.loads(sys.argv[1])
    limits = json.loads(sys.argv[2])
    for name, value in ((resource.RLIMIT_AS, limits['address_space_bytes']),
                        (resource.RLIMIT_CPU, limits['cpu_seconds']),
                        (resource.RLIMIT_FSIZE, limits['file_bytes']),
                        (resource.RLIMIT_NOFILE, limits['open_files']),
                        (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(name, (value, value))
    server = ThreadingHTTPServer(('127.0.0.1', 0), Bridge)
    Thread(target=server.serve_forever, daemon=True).start()
    os.environ['OPENAI_API_BASE'] = 'http://127.0.0.1:%d/v1' % server.server_port
    os.environ['OPENAI_API_KEY'] = 'isolated-fixture-not-a-provider-key'
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sys.exit(result.returncode)
    finally:
        server.shutdown()
        server.server_close()
