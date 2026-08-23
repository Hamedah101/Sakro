"""
Open this file first if you want to understand the Backblaze upload.

What Backblaze B2 is
    Online storage — a hard drive on the internet. You put files there so
    they are not only on this computer.

Words used below
    Bucket          A named folder in the cloud. Example: my-network-backups
    Key ID          Like a username for this app.
    Application Key Like a password. Anyone who has it can use your bucket.
    Endpoint        The web address of your Backblaze region.

Why we never print the Application Key
    Printing it (in the terminal, a flash message, or a log) would make it
    easy to steal. We save it only in the local .env file, which git ignores.

Default endpoint (change the region if Backblaze shows a different one)
    https://s3.us-west-004.backblazeb2.com
    Example other region: eu-central-003
    → https://s3.eu-central-003.backblazeb2.com

We talk to B2 with boto3, using the same API as Amazon S3. B2 understands it.
"""

import os
from datetime import datetime

# Folder that contains this file (the project folder).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# The local file we upload. You can point this at another CSV if you want.
TRAFFIC_PATH = os.path.join(BASE_DIR, "traffic.csv")

# Secrets live here. This file is listed in .gitignore so git will not upload it.
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Default US West. Change this if Backblaze showed you a different region.
DEFAULT_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"

# Names of the values we store. B2_APPLICATION_KEY is the secret.
B2_KEYS = ("B2_KEY_ID", "B2_APPLICATION_KEY", "B2_BUCKET", "B2_ENDPOINT")


def read_env_file():
    """Read key=value lines from the local .env file (no secrets printed)."""
    values = {}
    if not os.path.exists(ENV_PATH):
        return values
    with open(ENV_PATH, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def current_b2_settings():
    """Return Key ID, Application Key, bucket, and endpoint from the environment or .env."""
    file_values = read_env_file()
    settings = {}
    for key in B2_KEYS:
        settings[key] = os.environ.get(key, file_values.get(key, "")).strip()
    if not settings["B2_ENDPOINT"]:
        settings["B2_ENDPOINT"] = DEFAULT_ENDPOINT
    return settings


def write_b2_settings(key_id, app_key, bucket, endpoint):
    """Save Settings form values to .env and to the running program (os.environ)."""
    existing = read_env_file()
    existing["B2_KEY_ID"] = key_id
    # Empty password field means "keep the key we already saved".
    if app_key:
        existing["B2_APPLICATION_KEY"] = app_key
    existing["B2_BUCKET"] = bucket
    existing["B2_ENDPOINT"] = endpoint or DEFAULT_ENDPOINT

    lines = ["# Local secrets — do not share this file"]
    written = set()
    for key in B2_KEYS:
        lines.append(key + "=" + existing.get(key, ""))
        written.add(key)
    for key, value in existing.items():
        if key not in written:
            lines.append(key + "=" + value)

    with open(ENV_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    for key in B2_KEYS:
        os.environ[key] = existing.get(key, "")


def region_from_endpoint(endpoint):
    """Turn an endpoint URL into the region name boto3 needs (s3.REGION.backblazeb2.com)."""
    text = endpoint.replace("https://", "").replace("http://", "")
    parts = text.split(".")
    if len(parts) > 1 and parts[0] == "s3":
        return parts[1]
    return "us-west-004"


def make_cloud_filename():
    """
    Build the name the file will have inside the bucket.

    Try changing this yourself:
      return "traffic.csv"
    would always overwrite the same file instead of keeping dated copies.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return "traffic-" + stamp + ".csv"


def _friendly_upload_error(error):
    """Turn a boto3 error into a short message. We never include the secret."""
    name = error.__class__.__name__
    text = str(error)
    if "InvalidAccessKeyId" in text or "InvalidAccessKey" in text:
        return "Backblaze did not accept the Key ID. Check that you pasted the whole Key ID."
    if "SignatureDoesNotMatch" in text:
        return "Backblaze did not accept the Application Key. Paste it again in Settings."
    if "NoSuchBucket" in text:
        return "That bucket name was not found. Check the name on the Backblaze website."
    if "EndpointConnection" in name or "ConnectTimeout" in name or "NameResolution" in text:
        return "Could not reach the storage address. Check the endpoint and your internet."
    return "Could not save the copy. Check the key, bucket, and endpoint. (" + name + ")"


def upload_traffic_copy():
    """
    Upload traffic.csv to the Backblaze bucket.

    Returns (ok, message). ok is True on success.
    The message is safe to show on the Settings page (no secrets).
    """
    # Step 1 — read the keys you typed on Settings (from .env, never hardcoded).
    settings = current_b2_settings()
    key_id = settings["B2_KEY_ID"]
    app_key = settings["B2_APPLICATION_KEY"]
    bucket = settings["B2_BUCKET"]
    endpoint = settings["B2_ENDPOINT"] or DEFAULT_ENDPOINT

    if not key_id or not app_key or not bucket:
        return False, "Add your Backblaze Key ID, Application Key, and bucket in Settings first."

    # Step 2 — make sure the local file exists before we try to send it.
    if not os.path.exists(TRAFFIC_PATH):
        return False, "No traffic.csv file found yet. Capture some packets first."

    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        return False, "The boto3 package is missing. In a terminal, run: pip install boto3"

    filename = make_cloud_filename()
    try:
        # Step 3 — log in to Backblaze (B2 understands the same "s3" talk as Amazon).
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=app_key,
            region_name=region_from_endpoint(endpoint),
            config=Config(signature_version="s3v4"),
        )
        # Step 4 — send a copy of traffic.csv. The original file stays on this computer.
        client.upload_file(TRAFFIC_PATH, bucket, filename)
    except Exception as error:
        return False, _friendly_upload_error(error)

    return True, "Saved a copy as " + filename + " in your " + bucket + " bucket."
