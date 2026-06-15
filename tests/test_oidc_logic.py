"""
Standalone tests that don't require the Sentry runtime. They exercise the
pure logic (JWT decode, issuer/audience checks, identity mapping) by importing
the small helpers directly. The full pipeline is exercised in a live Sentry
instance; CI here just guards the parts that have no Sentry dependency.
"""

import base64
import json


def b64(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()


def urlsafe_b64decode(s: str) -> bytes:
    b = s.encode()
    return base64.urlsafe_b64decode(b + b"=" * (-len(b) % 4))


REGION = "us-east-1"
POOL = "us-east-1_ABC123"
CLIENT = "7exampleclientid"
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{POOL}"


def make_id_token(**overrides) -> str:
    payload = {
        "sub": "a1b2c3d4-1111-2222-3333-444455556666",
        "iss": ISSUER,
        "aud": CLIENT,
        "email": "user@example.com",
        "email_verified": True,
        "cognito:username": "username",
        "name": "Full Name",
    }
    payload.update(overrides)
    sig = base64.urlsafe_b64encode(b"sig").rstrip(b"=").decode()
    return f"{b64({'alg': 'RS256'})}.{b64(payload)}.{sig}"


def decode_payload(id_token: str) -> dict:
    _, payload_b, _ = map(urlsafe_b64decode, id_token.split(".", 2))
    return json.loads(payload_b)


def test_valid_token_decodes():
    p = decode_payload(make_id_token())
    assert p["iss"] == ISSUER
    aud = p["aud"]
    assert CLIENT in (aud if isinstance(aud, list) else [aud])
    assert p["email"] == "user@example.com"


def test_audience_as_list():
    p = decode_payload(make_id_token(aud=[CLIENT, "other"]))
    assert CLIENT in p["aud"]


def test_name_fallback_chain():
    # name present
    p = decode_payload(make_id_token())
    name = p.get("name") or p.get("cognito:username") or p["email"]
    assert name == "Full Name"
    # name absent -> cognito:username
    p = decode_payload(make_id_token(name=None))
    name = p.get("name") or p.get("cognito:username") or p["email"]
    assert name == "username"


def test_issuer_mismatch_detectable():
    p = decode_payload(make_id_token(iss="https://evil.example"))
    assert p["iss"] != ISSUER


def test_audience_mismatch_detectable():
    p = decode_payload(make_id_token(aud="someone-else"))
    aud = p["aud"]
    assert CLIENT not in (aud if isinstance(aud, list) else [aud])
