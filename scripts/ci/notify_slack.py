#!/usr/bin/env python3
"""Post one short TeveBot Agent notice to Slack through an incoming webhook.

Reads the webhook URL from the SLACK_WEBHOOK_URL environment variable. The URL is a secret:
it is never printed, logged or put in an error message.

Usage: notify_slack.py --event {pr_opened,checks_passed,checks_failed,review_posted}
                       [--repo OWNER/NAME] [--pr N] [--url LINK] [--dry-run]
Exit 0 = sent (or dry run), 2 = bad setup (missing/invalid webhook), 3 = send failed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

EVENTS = {
    "pr_opened": "PR opened",
    "checks_passed": "Checks passed",
    "checks_failed": "Checks FAILED",
    "review_posted": "Review posted",
}


def build_payload(event: str, repo: str, pr: str, url: str) -> dict:
    label = EVENTS[event]
    where = f"{repo} #{pr}" if repo and pr else (repo or "grid-pulse-builds")
    text = f"*TeveBot Agent:* {label} on {where}"
    if url:
        text += f"\n<{url}|Open the PR>"
    return {"text": text[:3000]}


def webhook_ok(url: str) -> bool:
    parts = urllib.parse.urlparse(url)
    if parts.scheme == "https" and parts.netloc:
        return True
    return parts.scheme == "http" and parts.hostname in {"127.0.0.1", "localhost"}  # local test receiver only


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--event", required=True, choices=sorted(EVENTS))
    ap.add_argument("--repo", default="")
    ap.add_argument("--pr", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    payload = build_payload(args.event, args.repo, args.pr, args.url)
    hook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if args.dry_run:
        print(json.dumps({"webhook": "set" if hook else "NOT SET", "payload": payload}, indent=2))
        return 0
    if not hook:
        print("SLACK_WEBHOOK_URL is not set; cannot notify Slack.", file=sys.stderr)
        return 2
    if not webhook_ok(hook):
        print("SLACK_WEBHOOK_URL is not a valid https URL.", file=sys.stderr)
        return 2
    req = urllib.request.Request(hook, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (scheme checked above)
            print(f"Slack accepted the notice (HTTP {resp.status}).")
            return 0
    except (urllib.error.URLError, OSError) as exc:
        print(f"Slack send failed: {type(exc).__name__}", file=sys.stderr)  # type only, never the URL
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
