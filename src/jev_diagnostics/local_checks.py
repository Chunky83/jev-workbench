"""An actual offline HTTP regression test, using synthetic data only."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def run_guest_fixture():
    secret = "synthetic-private-document"

    class FixtureHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            owner = self.headers.get("Authorization") == "Bearer synthetic-owner"
            self.send_response(200 if owner else 401)
            self.end_headers()
            self.wfile.write((secret if owner else "Authentication required").encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    observations = []
    try:
        for role, expected in (("guest", 401), ("owner", 200)):
            headers = {"Authorization": "Bearer synthetic-owner"} if role == "owner" else {}
            request = Request(f"http://127.0.0.1:{server.server_port}/private", headers=headers)
            try:
                response = urlopen(request, timeout=3)
            except HTTPError as error:
                response = error
            with response:
                status = response.code
                protected_content = secret in response.read().decode()
            passed = status == expected and protected_content == (role == "owner")
            observations.append({"id": f"E{len(observations) + 1:03}", "role": role,
                                 "status": status, "protected_content_present": protected_content,
                                 "expected_status": expected, "passed": passed})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    return {"source": "Local synthetic HTTP fixture, not your website",
            "observations": observations, "passed": all(item["passed"] for item in observations)}
