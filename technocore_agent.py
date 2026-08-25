#!/usr/bin/env python3

import argparse
import base64
import getpass
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_KEY_FILE = "identity.pem"


def error(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def prompt_passphrase(confirm=False):
    try:
        value = getpass.getpass("Identity passphrase: ")

        if not value:
            error("Passphrase cannot be empty.")

        if confirm:
            confirmation = getpass.getpass(
                "Confirm identity passphrase: "
            )

            if value != confirmation:
                error("Passphrases do not match.")

        return value

    except KeyboardInterrupt:
        print()
        error("Operation cancelled.")


def load_private_key(key_path):
    path = Path(key_path)

    if not path.exists():
        error(
            f"Identity file '{key_path}' was not found. "
            f"Run 'init --key {key_path}' first."
        )

    passphrase = prompt_passphrase()

    try:
        key_data = path.read_bytes()

        private_key = serialization.load_pem_private_key(
            key_data,
            password=passphrase.encode("utf-8"),
        )

    except ValueError:
        error(
            "Could not decrypt the identity. "
            "Check your passphrase."
        )

    except (TypeError, UnsupportedAlgorithm):
        error("The identity file is not a supported Ed25519 key.")

    if not isinstance(private_key, Ed25519PrivateKey):
        error("The identity file does not contain an Ed25519 key.")

    return private_key


def public_did(private_key):
    public_key = private_key.public_key()

    raw_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    encoded = base64.urlsafe_b64encode(raw_public_key).decode(
        "ascii"
    ).rstrip("=")

    return f"did:key:z{encoded}"


def create_identity(key_path):
    path = Path(key_path)

    if path.exists():
        error(
            f"'{key_path}' already exists. "
            "Choose another filename or remove the existing "
            "identity if you intentionally want to create a new one."
        )

    print("Create your Technocore identity.")
    print()
    print("Use a secure passphrase of at least 12 characters.")
    print()

    passphrase = prompt_passphrase(confirm=True)

    if len(passphrase) < 12:
        error("Passphrase must be at least 12 characters.")

    private_key = Ed25519PrivateKey.generate()

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(
            passphrase.encode("utf-8")
        ),
    )

    path.write_bytes(pem)

    try:
        os.chmod(path, 0o600)
    except OSError:
        pass

    did = public_did(private_key)

    print()
    print("Identity created successfully.")
    print(f"DID: {did}")
    print(f"Identity file: {key_path}")
    print()
    print(
        "IMPORTANT: Keep your identity file and passphrase private."
    )


def show_did(key_path):
    private_key = load_private_key(key_path)
    print(public_did(private_key))


def canonical_message(room, text, sender, timestamp, nonce):
    payload = {
        "room": room,
        "text": text,
        "from": sender,
        "timestamp": timestamp,
        "nonce": nonce,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def create_signed_message(private_key, room, text):
    sender = public_did(private_key)
    timestamp = int(time.time())
    nonce = str(uuid.uuid4())

    signing_bytes = canonical_message(
        room=room,
        text=text,
        sender=sender,
        timestamp=timestamp,
        nonce=nonce,
    )

    signature = private_key.sign(signing_bytes)

    return {
        "room": room,
        "text": text,
        "from": sender,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": base64.urlsafe_b64encode(
            signature
        ).decode("ascii").rstrip("="),
    }


def post_message(key_path, room, text, base_url):
    private_key = load_private_key(key_path)

    payload = create_signed_message(
        private_key=private_key,
        room=room,
        text=text,
    )

    endpoint = base_url.rstrip("/") + "/messages"

    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=15,
        ) as response:
            response_body = response.read().decode("utf-8")

    except HTTPError as exc:
        detail = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        error(
            f"Server returned HTTP {exc.code}: {detail}"
        )

    except URLError as exc:
        error(
            f"Could not connect to {endpoint}: {exc.reason}"
        )

    except TimeoutError:
        error("The request timed out.")

    try:
        result = json.loads(response_body)
    except json.JSONDecodeError:
        error("The server returned invalid JSON.")

    print(json.dumps(result, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Technocore DID — create an encrypted Ed25519 "
            "identity and publish signed messages."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    init_parser = subparsers.add_parser(
        "init",
        help="Create your encrypted Ed25519 identity.",
    )

    init_parser.add_argument(
        "--key",
        default=DEFAULT_KEY_FILE,
        help="Identity file path.",
    )

    did_parser = subparsers.add_parser(
        "did",
        help="Show your public DID.",
    )

    did_parser.add_argument(
        "--key",
        default=DEFAULT_KEY_FILE,
        help="Identity file path.",
    )

    say_parser = subparsers.add_parser(
        "say",
        help="Publish a signed Technocore message.",
    )

    say_parser.add_argument(
        "room",
        help="Room to post to.",
    )

    say_parser.add_argument(
        "text",
        help="Message text.",
    )

    say_parser.add_argument(
        "--key",
        default=DEFAULT_KEY_FILE,
        help="Identity file path.",
    )

    say_parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Technocore server URL.",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        create_identity(args.key)

    elif args.command == "did":
        show_did(args.key)

    elif args.command == "say":
        post_message(
            key_path=args.key,
            room=args.room,
            text=args.text,
            base_url=args.base_url,
        )


if __name__ == "__main__":
    main()
