#!/usr/bin/env python3
"""
gitblurb backend server
Run with: python server.py
"""

from flask import Flask, request, jsonify
import os
import json
import urllib.request
import urllib.error

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

def load_config():
    config_path = os.path.join(os.path.expanduser("~"), ".gitblurb_config")
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config

config = load_config()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "") or config.get("ANTHROPIC_API_KEY", "")

# Valid license keys — we'll manage these manually for now
# Format: "license-key": "customer-email"
VALID_LICENSES = {
    "FREE_TRIAL": "free_trial",  # built-in free trial key
    # Add paying customer keys here as they come in:
    # "GITBLURB-XXXX-XXXX-XXXX": "customer@email.com",
}

FREE_TRIAL_LIMIT = 20

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

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    diff = data.get("diff", "").strip()
    branch = data.get("branch", "unknown")
    license_key = data.get("license_key", "").strip()

    # Validate input
    if not diff:
        return jsonify({"error": "No diff provided"}), 400

    if not license_key:
        return jsonify({"error": "No license key provided"}), 401

    # Validate license key
    if license_key not in VALID_LICENSES:
        return jsonify({"error": "Invalid license key"}), 401

    # Check API key
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "Server misconfigured"}), 500

    # Call Claude
    try:
        result = call_claude(diff, branch)
        return jsonify({"description": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Claude ────────────────────────────────────────────────────────────────────

def call_claude(diff, branch_name):
    user_message = f"Branch: {branch_name}\n\nDiff:\n{diff}"

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST"
    )

    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data["content"][0]["text"]


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not ANTHROPIC_API_KEY:
        print("❌  No API key found. Add ANTHROPIC_API_KEY to ~/.gitblurb_config")
    else:
        print("✅  API key loaded")
        print("🚀  Starting gitblurb server on http://localhost:5000")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)