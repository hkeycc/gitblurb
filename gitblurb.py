#!/usr/bin/env python3
"""
gitblurb - AI-powered PR description generator
Usage: python gitblurb.py
"""

import urllib.request
import urllib.error
import subprocess
import sys
import os
import json

# ── Config ────────────────────────────────────────────────────────────────────
def load_config():
    config_path = os.path.join(os.path.expanduser("~"), ".gitblurb_config")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return ""
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FREE_USES_FILE = os.path.expanduser("~/.gitblurb_uses")
FREE_LIMIT = 20

SYSTEM_PROMPT = """You are an expert software engineer writing a GitHub pull request description.
Given a git diff, produce:
1. A concise PR title (max 72 chars) starting with a verb e.g. "Add", "Fix", "Refactor", "Update"
2. A short description with:
   - ## What changed — bullet points of the main changes (max 5 bullets)
   - ## Why — one sentence explaining the reason/motiv+ation
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

def check_api_key():
    if not ANTHROPIC_API_KEY:
        print("\n❌  No API key found.")
        print("    Get one at: https://console.anthropic.com")
        print("    Then run:   set ANTHROPIC_API_KEY=your-key-here\n")
        sys.exit(1)

def get_git_diff(base_branch="main"):
    """Get the diff of the current branch vs base branch."""
    # First try: diff vs base branch
    result = subprocess.run(
    ["git", "diff", base_branch + "...HEAD"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
    if result.returncode != 0:
        # Fallback: diff of staged + unstaged changes
        result = subprocess.run(
    ["git", "diff", base_branch + "...HEAD"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
    if result.returncode != 0:
        print("\n❌  Could not get git diff. Are you inside a git repo?\n")
        sys.exit(1)

    diff = result.stdout.strip()
    if not diff:
        # Try staged only
        result = subprocess.run(
    ["git", "diff", base_branch + "...HEAD"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
        diff = result.stdout.strip()

    if not diff:
        print("\n⚠️   No changes detected vs", base_branch)
        print("    Make sure you have commits or staged changes on your branch.\n")
        sys.exit(0)

    # Truncate very large diffs to avoid token limits
    if len(diff) > 12000:
        diff = diff[:12000] + "\n\n[diff truncated for length]"

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
        "http://localhost:5000/generate",
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
        print(f"\n❌  Server error {e.code}: {error_body}\n")
        sys.exit(1)
    except urllib.error.URLError:
        print("\n❌  Could not connect to server. Is it running?\n")
        sys.exit(1)

def copy_to_clipboard(text):
    """Copy text to Windows clipboard."""
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
    print("\n" + "─" * 60)
    print("  🎉  You've used all 20 free uses!")
    print()
    print("  To keep using gitblurb, subscribe for $9/month:")
    print("  👉  https://your-stripe-link-here.com")
    print()
    print("  After subscribing, set your license key:")
    print("  set GITBLURB_LICENSE=your-license-key")
    print("─" * 60 + "\n")
    sys.exit(0)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n🔍  gitblurb — AI PR Description Generator")
    print("─" * 60)

    

    # Check free usage limit
    # (Skip limit check if a license key is set)
    has_license = bool(os.environ.get("GITBLURB_LICENSE", ""))
    if not has_license:
        uses = get_use_count()
        remaining = FREE_LIMIT - uses
        if uses >= FREE_LIMIT:
            show_paywall()
        print(f"  Free uses remaining: {remaining - 1}")

    # Get base branch from args or default to main
    base_branch = sys.argv[1] if len(sys.argv) > 1 else "main"

    # Get diff
    branch = get_branch_name()
    print(f"  Branch: {branch}")
    print(f"  Comparing vs: {base_branch}")
    print("  Generating PR description...\n")

    diff = get_git_diff(base_branch)

    # Call Claude
    result = call_server(diff, branch)

    # Increment use count
    if not has_license:
        increment_use_count()

    # Print result
    print("─" * 60)
    print(result)
    print("─" * 60)

    # Copy to clipboard
    if copy_to_clipboard(result):
        print("\n✅  Copied to clipboard — paste it straight into GitHub.\n")
    else:
        print("\n✅  Done — copy the text above into your PR.\n")

if __name__ == "__main__":
    main()