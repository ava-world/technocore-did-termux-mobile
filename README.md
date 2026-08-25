# Technocore DID — Mobile Tutorial

A beginner-friendly, mobile-first guide for creating an encrypted Ed25519 DID and publishing signed Technocore messages using Termux on Android.

The goal is simple: **clone the repository, follow the steps in order, and publish your first signed Technocore message entirely from your phone.**

## What You Will Build

By following this tutorial, you will:

1. Set up Python and the required tools in Termux.
2. Create an encrypted Ed25519 identity.
3. Generate your own `did:key` DID.
4. Post a signed introduction message.
5. Publish a signed contribution message.
6. Verify the server response and save your participation evidence.

Your private key stays on your device.

## Requirements

You need:

* An Android phone
* Internet access
* Termux
* A secure passphrase of at least 12 characters

Install Termux before starting.

> **Important:** Keep your `identity.pem` private. Never upload it to GitHub, send it to anyone, or paste its contents into a public chat.

---

## Step 1 — Update Termux

Open Termux and run:

```bash
pkg update -y && pkg upgrade -y
```

Wait for the update to finish before continuing.

---

## Step 2 — Install the Required Packages

Install Git, Python, the required build tools, and the Termux cryptography package:

```bash
pkg install git python clang libffi openssl rust python-cryptography -y
```

The project uses Python's `cryptography` package for Ed25519 operations.

You do **not** need to install PyNaCl or manually build an alternative cryptography implementation.

---

## Step 3 — Clone the Repository

Clone this repository:

```bash
git clone https://github.com/ava-world/technocore-did-termux-mobile.git
```

Enter the repository:

```bash
cd technocore-did-mobile
```

---

## Step 4 — Create the Python Environment

Create a virtual environment that can use the tested Termux cryptography package:

```bash
python -m venv --system-site-packages .venv
```

Activate it:

```bash
source .venv/bin/activate
```

You should now see `(.venv)` at the beginning of your Termux prompt.

---

## Step 5 — Upgrade pip

Run:

```bash
python -m pip install --upgrade pip
```

Then install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

The repository intentionally uses the tested `cryptography` approach instead of asking mobile users to compile PyNaCl.

---

## Step 6 — Verify the Setup

Before creating your identity, verify that Python can access `cryptography`:

```bash
python -c "import cryptography; print('cryptography OK:', cryptography.__version__)"
```

You should see something similar to:

```text
cryptography OK: 48.0.1
```

Now verify that the Technocore agent can load:

```bash
python -c "import runpy; runpy.run_path('technocore_agent.py'); print('Agent loaded successfully')"
```

You should see:

```text
Agent loaded successfully
```

If both checks succeed, your mobile environment is ready.

---

## Step 7 — Create Your Encrypted DID

Create your identity:

```bash
python technocore_agent.py init --key identity.pem
```

You will be asked to create a passphrase.

Use a strong passphrase of at least 12 characters.

The command creates:

```text
identity.pem
```

This file contains your encrypted private identity.

**Do not share it.**

---

## Step 8 — Show Your Public DID

Run:

```bash
python technocore_agent.py did --key identity.pem
```

Enter your identity passphrase when prompted.

You should receive a DID that looks similar to:

```text
did:key:z...
```

This is your public DID.

Your DID can be shared publicly.

Your private key cannot.

---

## Step 9 — Start the Local Technocore Test Server

Before publishing to the real Technocore service, start the local mock server.

Run:

```bash
nohup python src/mock_server.py --host 127.0.0.1 --port 8000 &>/dev/null &
```

This gives you a safe local environment for testing the signed-message flow.

---

## Step 10 — Post Your First Signed Introduction

Before making a contribution, introduce yourself to Technocore.

Run:

```bash
python technocore_agent.py say lobby "Hello from a new Technocore contributor. I just joined Technocore with my mobile." --key identity.pem --base-url http://127.0.0.1:8000
```

Enter your `identity.pem` passphrase when prompted.

The JSON response includes:

* The server-assigned sequence
* Timestamp
* Your public DID
* Nonce
* Stored message text

Save the **room** and **sequence** as participation evidence.

You can also take a screenshot of the successful terminal response.

---

## Step 11 — Publish Your Contribution

Now create a public contribution.

Your contribution can be:

* An X/Twitter post
* A short video
* An article
* A graphic
* A translation
* A tutorial
* Another publicly accessible resource

The contribution should provide something useful to other people.

Copy the public URL of your contribution.

---

## Step 12 — Post Your Contribution to Technocore

Replace `PUBLIC_CONTRIBUTION_URL` with your actual public URL.

Replace `SHORT_DESCRIPTION` with a short explanation of what your contribution does.

Run:

```bash
python technocore_agent.py say technocore "I published a contribution: PUBLIC_CONTRIBUTION_URL. It helps people understand SHORT_DESCRIPTION." --key identity.pem --base-url http://127.0.0.1:8000
```

Enter your identity passphrase when prompted.

The response should contain the signed message and server-assigned information.

Save the response as evidence.

---

## What Your Contribution Should Contain

Try to make your contribution clear and useful.

Where appropriate, include your public DID:

```text
did:key:...
```

Do not include:

* Your private key
* Your `identity.pem` contents
* Your identity passphrase
* Any secret credentials

---

## Participation Evidence

Keep evidence of your participation.

At minimum, save:

1. Your public DID.
2. The room where you posted.
3. The server-assigned sequence number.
4. A screenshot of your successful signed message.
5. The public URL of your contribution.

Your private key should **never** be used as participation evidence.

---

## Optional — Run the Tests

If you want to run the project's tests:

```bash
pytest -q
```

---

## Troubleshooting

### `cryptography` Cannot Be Imported

Check that the Termux package is installed:

```bash
pkg install python-cryptography -y
```

Then recreate the virtual environment using the tested setup:

```bash
deactivate
rm -rf .venv
python -m venv --system-site-packages .venv
source .venv/bin/activate
```

Verify again:

```bash
python -c "import cryptography; print('cryptography OK:', cryptography.__version__)"
```

---

### The Agent Cannot Load

Run:

```bash
python -c "import runpy; runpy.run_path('technocore_agent.py'); print('Agent loaded successfully')"
```

If this succeeds, the Python agent itself can load correctly.

---

### The Local Server Is Not Responding

Restart it:

```bash
nohup python src/mock_server.py --host 127.0.0.1 --port 8000 &>/dev/null &
```

Then retry the message command.

---

### I Forgot to Activate the Virtual Environment

Run:

```bash
source .venv/bin/activate
```

You should see:

```text
(.venv)
```

at the beginning of your Termux prompt.

---

## Security

Your identity is based on Ed25519 public-key cryptography.

The most important rule is:

> **Your private key belongs only to you.**

Never:

* Upload `identity.pem` to GitHub.
* Send `identity.pem` to another person.
* Paste the contents of `identity.pem` into an issue or chat.
* Publish your identity passphrase.
* Commit private credentials to the repository.

Your public DID is safe to share.

---

## You Are Done

At the end of this tutorial you should have:

* A working mobile Python environment.
* An encrypted Ed25519 identity.
* A public `did:key`.
* A signed introduction message.
* A signed contribution message.
* Participation evidence.

Everything can be completed from an Android phone using Termux.
