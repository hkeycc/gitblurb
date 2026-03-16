#!/usr/bin/env python3
"""
gitblurb - AI-powered PR description generator
Usage: python gitblurb.py [base-branch]
"""

import urllib.request
import urllib.error
import subprocess
import sys
import os
import json

# ── Config ────────────────────────────────────────────────────────────────────

FREE_USES_FILE = os.path.expanduser("~/.gitblurb_uses")
FREE_LIMIT = 50
SERVER_URL = "https://gitblurb.onrender.com/generate"

SYSTEM_PROMPT = """You are an expert software engineer writing a GitHub pull request description.
Given a git diff, produce:
1. A concise PR title (max 72 chars) starting with a verb e.g. "Add", "Fix", "Refactor", "Update"
2. A short description with:
   - ## What changed — bullet points of the main changes (max 5 bullets)
   - ## Why — one sentence explaining the reason/motivation
   - ## Testing — one sentence on how to test this (if obvious from the diff)

Be specific and technical. Use the actual file names, function names, and variable names from the diff.
Do NOT say "this PR", do NOT use vague language like "various improvements".
Output plain text only — no markdown code fences wrapping the whole response."""

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_use_count():
    try:
        with open(FREE_USES_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0

def increment_use_count():
    count = get_use_count() + 1
    with open(FREE_USES_FILE, "w") as f:
        f.write(str(count))
    return count

def get_git_diff(base_branch="main"):
    result = subprocess.run(
        ["git", "diff", base_branch + "...HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
    if result.returncode != 0:
        print("error: could not get git diff. Are you inside a git repo?")
        sys.exit(1)

    diff = result.stdout.strip()

    if not diff:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        diff = result.stdout.strip()

    if not diff:
        print(f"error: no changes detected vs {base_branch}")
        print("make sure you have commits or staged changes on your branch.")
        sys.exit(0)

    if len(diff) > 12000:
        diff = diff[:12000] + "\n\n[diff truncated]"

    return diff

def get_branch_name():
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"

def call_server(diff, branch_name):
    license_key = os.environ.get("GITBLURB_LICENSE", "FREE_TRIAL")
    payload = json.dumps({
        "diff": diff,
        "branch": branch_name,
        "license_key": license_key
    }).encode("utf-8")

    req = urllib.request.Request(
        SERVER_URL,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["description"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"error: server returned {e.code}: {error_body}")
        sys.exit(1)
    except urllib.error.URLError:
        print("error: could not connect to server.")
        sys.exit(1)

def copy_to_clipboard(text):
    try:
        subprocess.run(
            ["clip"],
            input=text.encode("utf-8"),
            check=True,
            capture_output=True
        )
        return True
    except:
        return False

def show_paywall():
    print("error: usage limit reached. visit https://github.com/hkeycc/gitblurb for more info.")
    sys.exit(0)
    

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    has_license = bool(os.environ.get("GITBLURB_LICENSE", ""))
    if not has_license:
        uses = get_use_count()
        remaining = FREE_LIMIT - uses
        if uses >= FREE_LIMIT:
            show_paywall()

    base_branch = sys.argv[1] if len(sys.argv) > 1 else "main"
    branch = get_branch_name()

    print(f"gitblurb: {branch} -> {base_branch}")
    
    print("generating...\n")

    diff = get_git_diff(base_branch)
    result = call_server(diff, branch)

    if not has_license:
        increment_use_count()

    print("-" * 60)
    print(result)
    print("-" * 60)

    if copy_to_clipboard(result):
        print("\ncopied to clipboard.\n")
    else:
        print("\ndone.\n")

if __name__ == "__main__":
    main()
