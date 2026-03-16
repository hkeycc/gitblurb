#!/usr/bin/env python3
"""
gitblurb test suite
Run with: python test.py
"""

import urllib.request
import urllib.error
import json
import sys

BASE_URL = "https://gitblurb.onrender.com"
PASS = "✅"
FAIL = "❌"
results = []

def test(name, fn):
    try:
        fn()
        print(f"{PASS}  {name}")
        results.append(True)
    except Exception as e:
        print(f"{FAIL}  {name}: {e}")
        results.append(False)

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_health():
    with urllib.request.urlopen(f"{BASE_URL}/health") as r:
        data = json.loads(r.read())
        assert data["status"] == "ok", f"Expected 'ok', got {data}"

def test_generate_valid():
    payload = json.dumps({
        "diff": "diff --git a/app.py b/app.py\n+def greet(name):\n+    return f'Hello, {name}'",
        "branch": "feature/add-greet",
        "license_key": "FREE_TRIAL"
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/generate",
        data=payload,
        headers={"content-type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        assert "description" in data, "No description in response"
        assert len(data["description"]) > 20, "Description too short"

def test_generate_no_license():
    payload = json.dumps({
        "diff": "some diff",
        "branch": "test",
        "license_key": ""
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/generate",
        data=payload,
        headers={"content-type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req)
        raise AssertionError("Should have returned 401")
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"

def test_generate_invalid_license():
    payload = json.dumps({
        "diff": "some diff",
        "branch": "test",
        "license_key": "INVALID-KEY-123"
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/generate",
        data=payload,
        headers={"content-type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req)
        raise AssertionError("Should have returned 401")
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"

def test_generate_no_diff():
    payload = json.dumps({
        "diff": "",
        "branch": "test",
        "license_key": "FREE_TRIAL"
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/generate",
        data=payload,
        headers={"content-type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req)
        raise AssertionError("Should have returned 400")
    except urllib.error.HTTPError as e:
        assert e.code == 400, f"Expected 400, got {e.code}"

# ── Run ───────────────────────────────────────────────────────────────────────

print("\n gitblurb test suite")
print("─" * 40)

test("Server health check", test_health)
test("Generate with valid license", test_generate_valid)
test("Reject empty license key", test_generate_no_license)
test("Reject invalid license key", test_generate_invalid_license)
test("Reject empty diff", test_generate_no_diff)

print("─" * 40)
passed = sum(results)
total = len(results)
print(f"\n  {passed}/{total} tests passed\n")

if passed < total:
    sys.exit(1)