import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "notify_slack.py"
FAKE = "https://hooks.slack.test/services/T000/B000/DONOTLEAKTHISVALUE"


def run(args, env_url=None):
    env = {k: v for k, v in os.environ.items() if k != "SLACK_WEBHOOK_URL"}
    if env_url:
        env["SLACK_WEBHOOK_URL"] = env_url
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)


class NotifyTests(unittest.TestCase):
    def test_N1_dry_run_masks_url(self):
        r = run(["--event", "pr_opened", "--repo", "o/r", "--pr", "7", "--dry-run"], FAKE)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("DONOTLEAK", r.stdout + r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["webhook"], "set")
        self.assertIn("TeveBot Agent", out["payload"]["text"])

    def test_N1_missing_webhook_fails_loud(self):
        r = run(["--event", "checks_failed"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("SLACK_WEBHOOK_URL", r.stderr)

    def test_N1_non_https_rejected_without_echo(self):
        r = run(["--event", "pr_opened"], "http://evil.example/DONOTLEAK")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("DONOTLEAK", r.stdout + r.stderr)

    def test_N1_payload_bounded(self):
        r = run(["--event", "pr_opened", "--url", "x" * 5000, "--dry-run"], FAKE)
        self.assertLessEqual(len(json.loads(r.stdout)["payload"]["text"]), 3000)

    def test_N1_unreachable_webhook_fails_without_url_in_output(self):
        r = run(["--event", "pr_opened"], "https://127.0.0.1:1/DONOTLEAK")
        self.assertEqual(r.returncode, 3)
        self.assertNotIn("DONOTLEAK", r.stdout + r.stderr)

    def test_N1_posts_to_local_receiver(self):
        got = {}

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                got["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            r = run(["--event", "checks_passed", "--repo", "o/r", "--pr", "9"], f"http://127.0.0.1:{srv.server_port}/hook")
        finally:
            srv.shutdown()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Checks passed", got["body"]["text"])


if __name__ == "__main__":
    unittest.main()
