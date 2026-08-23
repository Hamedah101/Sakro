import os
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "sakro-dev-only-change-me")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAFFIC_PATH = os.path.join(BASE_DIR, "traffic.csv")
ENV_PATH = os.path.join(BASE_DIR, ".env")
DEFAULT_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"
B2_KEYS = ("B2_KEY_ID", "B2_APPLICATION_KEY", "B2_BUCKET", "B2_ENDPOINT")
PROTOCOL_NAMES = {1: "ICMP", 6: "TCP", 17: "UDP"}


def protocol_name(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return str(value or "?")
    return PROTOCOL_NAMES.get(number, "Type " + str(number))


def is_unusual(value):
    try:
        return int(float(value)) == -1
    except (TypeError, ValueError):
        return False


def load_traffic():
    columns = ["Source", "Destination", "Protocol", "Length", "Prediction"]
    if not os.path.exists(TRAFFIC_PATH):
        return pd.DataFrame(columns=columns)
    try:
        data = pd.read_csv(TRAFFIC_PATH, on_bad_lines="skip")
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError):
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in data.columns:
            data[column] = 1
    return data


def packet_records(data):
    records = []
    for row in data.to_dict(orient="records"):
        unusual = is_unusual(row.get("Prediction"))
        records.append({
            "source": row.get("Source", ""),
            "destination": row.get("Destination", ""),
            "protocol": protocol_name(row.get("Protocol", "")),
            "length": row.get("Length", ""),
            "unusual": unusual,
            "risk": "High" if unusual else "Low",
            "risk_class": "high" if unusual else "low",
            "note": (
                "This packet looked different from most of the others. That can be a real problem, or just something uncommon."
                if unusual else
                "This packet looked like normal traffic."
            ),
        })
    return records


def network_stats(data):
    total = len(data)
    threats = int(data["Prediction"].map(is_unusual).sum()) if total else 0
    if threats > 10:
        risk = "High"
    elif threats > 5:
        risk = "Medium"
    else:
        risk = "Low"
    return {
        "total_packets": total,
        "threats": threats,
        "risk": risk,
        "risk_class": risk.lower(),
    }


def looks_local(ip):
    text = str(ip)
    return text.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.", "127."))


def device_list(data):
    seen = []
    names = {}
    for row in data.to_dict(orient="records"):
        for ip in (row.get("Source"), row.get("Destination")):
            if ip and ip not in names:
                names[ip] = "This network" if looks_local(ip) else "Outside"
                seen.append({"ip": ip, "place": names[ip]})
    return seen


def protocol_counts(data):
    counts = {}
    for value in data.get("Protocol", []):
        name = protocol_name(value)
        counts[name] = counts.get(name, 0) + 1
    return counts


def activity_items(records):
    items = []
    for packet in records[-6:][::-1]:
        items.append({
            "text": packet["protocol"] + " from " + str(packet["source"]) + " to " + str(packet["destination"]),
            "kind": "danger" if packet["unusual"] else "",
            "time": "in file",
        })
    if not items:
        items.append({"text": "No packets in traffic.csv yet.", "kind": "", "time": ""})
    return items


def page_data():
    data = load_traffic()
    stats = network_stats(data)
    records = packet_records(data)
    return data, stats, records


def read_env_file():
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
    file_values = read_env_file()
    settings = {}
    for key in B2_KEYS:
        settings[key] = os.environ.get(key, file_values.get(key, "")).strip()
    if not settings["B2_ENDPOINT"]:
        settings["B2_ENDPOINT"] = DEFAULT_ENDPOINT
    return settings


def write_b2_settings(key_id, app_key, bucket, endpoint):
    existing = read_env_file()
    existing["B2_KEY_ID"] = key_id
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
    text = endpoint.replace("https://", "").replace("http://", "")
    parts = text.split(".")
    if len(parts) > 1 and parts[0] == "s3":
        return parts[1]
    return "us-west-004"


def upload_traffic_copy():
    settings = current_b2_settings()
    key_id = settings["B2_KEY_ID"]
    app_key = settings["B2_APPLICATION_KEY"]
    bucket = settings["B2_BUCKET"]
    endpoint = settings["B2_ENDPOINT"] or DEFAULT_ENDPOINT

    if not key_id or not app_key or not bucket:
        return False, "Add your Backblaze Key ID, Application Key, and bucket in Settings first."

    if not os.path.exists(TRAFFIC_PATH):
        return False, "No traffic.csv file found yet. Capture some packets first."

    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        return False, "The boto3 package is missing. In a terminal, run: pip install boto3"

    filename = "traffic-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv"
    try:
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=app_key,
            region_name=region_from_endpoint(endpoint),
            config=Config(signature_version="s3v4"),
        )
        client.upload_file(TRAFFIC_PATH, bucket, filename)
    except Exception as error:
        return False, "Could not save the copy. Check the key, bucket, and endpoint. (" + error.__class__.__name__ + ")"

    return True, "Saved a copy as " + filename + " in your " + bucket + " bucket."


@app.context_processor
def inject_defaults():
    return {"show_alerts": session.get("show_alerts", True)}


@app.route("/")
def home():
    data, stats, records = page_data()
    return render_template(
        "index.html",
        active_page="dashboard",
        packets=records,
        activity=activity_items(records),
        **stats,
    )


@app.route("/map")
def network_map():
    data, stats, records = page_data()
    devices = device_list(data)
    return render_template(
        "map.html",
        active_page="map",
        devices=devices,
        device_count=len(devices),
        **stats,
    )


@app.route("/threats")
def threats_page():
    data, stats, records = page_data()
    flagged = [row for row in records if row["unusual"]]
    return render_template(
        "threats.html",
        active_page="threats",
        flagged=flagged,
        **stats,
    )


@app.route("/analytics")
def analytics_page():
    data, stats, records = page_data()
    return render_template(
        "analytics.html",
        active_page="analytics",
        protocol_counts=protocol_counts(data),
        device_count=len(device_list(data)),
        **stats,
    )


@app.route("/bot")
def bot_page():
    data, stats, records = page_data()
    return render_template(
        "bot.html",
        active_page="bot",
        **stats,
    )


@app.route("/settings", methods=["GET"])
def settings_page():
    data, stats, records = page_data()
    settings = current_b2_settings()
    return render_template(
        "settings.html",
        active_page="settings",
        b2_key_id=settings["B2_KEY_ID"],
        b2_bucket=settings["B2_BUCKET"],
        b2_endpoint=settings["B2_ENDPOINT"],
        key_saved=bool(settings["B2_APPLICATION_KEY"]),
        show_alerts=session.get("show_alerts", True),
        **stats,
    )


@app.route("/settings/save", methods=["POST"])
def save_settings():
    session["show_alerts"] = request.form.get("show_alerts") == "on"
    write_b2_settings(
        request.form.get("b2_key_id", "").strip(),
        request.form.get("b2_application_key", "").strip(),
        request.form.get("b2_bucket", "").strip(),
        request.form.get("b2_endpoint", "").strip(),
    )
    flash("Settings saved on this computer.", "ok")
    return redirect(url_for("settings_page"))


@app.route("/settings/upload", methods=["POST"])
def upload_b2():
    ok, message = upload_traffic_copy()
    flash(message, "ok" if ok else "bad")
    return redirect(url_for("settings_page"))


@app.route("/about")
def about_page():
    data, stats, records = page_data()
    return render_template(
        "about.html",
        active_page="about",
        **stats,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
