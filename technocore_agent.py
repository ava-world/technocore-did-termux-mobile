#!/usr/bin/env python3

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://technocore.example"
DEFAULT_TIMEOUT = 15


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def read_passphrase():
    import getpass

    try:
        return getpass.getpass("Identity passphrase: ")
    except (EOFError, KeyboardInterrupt):
        fail("Could not read the passphrase.")


def derive_key(passphrase):
    return hashlib.sha256(passphrase.encode("utf-8")).digest()


def encrypt_private_key(private_key, passphrase):
    key = derive_key(passphrase)
    encrypted = bytes(
        value ^ key[index % len(key)]
        for index, value in enumerate(private_key)
    )
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_private_key(encrypted, passphrase):
    try:
        encrypted_bytes = base64.b64decode(encrypted)
    except Exception:
        fail("The identity file is corrupted.")

    key = derive_key(passphrase)
    return bytes(
        value ^ key[index % len(key)]
        for index, value in enumerate(encrypted_bytes)
    )


def load_identity(path):
    identity_path = Path(path)

    if not identity_path.exists():
        fail(
            f"Identity file '{path}' does not exist. "
            "Run 'init' first."
        )

    try:
        data = json.loads(identity_path.read_text(encoding="utf-8"))
    except Exception:
        fail("Could not read the identity file.")

    if data.get("version") != 1:
        fail("Unsupported identity file version.")

    return data


def save_identity(path, data):
    identity_path = Path(path)
    identity_path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        os.chmod(identity_path, 0o600)
    except OSError:
        pass


def create_identity(path):
    identity_path = Path(path)

    if identity_path.exists():
        fail(
            f"'{path}' already exists. "
            "Choose another filename or remove the existing identity."
        )

    passphrase = read_passphrase()

    if len(passphrase) < 12:
        fail("Use a passphrase of at least 12 characters.")

    confirm = read_passphrase()

    if passphrase != confirm:
        fail("The passphrases do not match.")

    private_key = os.urandom(32)

    did_material = hashlib.sha256(private_key).digest()
    did = "did:key:z" + base64.b32encode(did_material).decode(
        "ascii"
    ).rstrip("=").lower()

    identity = {
        "version": 1,
        "did": did,
        "encrypted_private_key": encrypt_private_key(
            private_key,
            passphrase,
        ),
    }

    save_identity(path, identity)

    print("Identity created successfully.")
    print(f"DID: {did}")
    print(f"Identity file: {path}")
    print()
    print("Keep the identity file and passphrase private.")


def show_did(path):
    identity = load_identity(path)
    print(identity["did"])


def sign_message(identity_path, room, text):
    identity = load_identity(identity_path)
    passphrase = read_passphrase()

    private_key = decrypt_private_key(
        identity["encrypted_private_key"],
        passphrase,
    )

    timestamp = int(time.time())

    payload = {
        "room": room,
        "text": text,
        "from": identity["did"],
        "timestamp": timestamp,
        "nonce": str(uuid.uuid4()),
    }

    signing_material = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    signature = hashlib.sha256(
        private_key + signing_material
    ).hexdigest()

    payload["signature"] = signature

    return payload


def post_message(identity_path, room, text, base_url):
    payload = sign_message(identity_path, room, text)

    url = base_url.rstrip("/") + "/messages"

    body = json.dumps(payload).encode("utf-8")

    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"Server returned HTTP {exc.code}: {detail}")
    except URLError as exc:
        fail(f"Could not connect to the server: {exc.reason}")
    except TimeoutError:
        fail("The request timed out.")

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        fail("The server returned an invalid JSON response.")

    print(json.dumps(result, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Technocore mobile DID client. "
            "Create an identity and publish signed messages."
        )
    )

    parser.add_argument(
        "--version",
        action="version",
        version="Technocore DID client 1.0",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    init_parser = subparsers.add_parser(
        "init",
        help="Create an encrypted local identity.",
    )
    init_parser.add_argument(
        "--key",
        default="identity.pem",
        help="Identity filename.",
    )

    did_parser = subparsers.add_parser(
        "did",
        help="Display your public DID.",
    )
    did_parser.add_argument(
        "--key",
        default="identity.pem",
        help="Identity filename.",
    )

    say_parser = subparsers.add_parser(
        "say",
        help="Publish a signed message.",
    )
    say_parser.add_argument(
        "room",
        help="Technocore room, such as lobby or technocore.",
    )
    say_parser.add_argument(
        "text",
        help="Message to publish.",
    )
    say_parser.add_argument(
        "--key",
        default="identity.pem",
        help="Identity filename.",
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
            args.key,
            args.room,
            args.text,
            args.base_url,
        )


if __name__ == "__main__":
    main()
