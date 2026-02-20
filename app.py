from __future__ import annotations

import base64
import io
import json
import os
import csv
import datetime
from pathlib import Path
from urllib.parse import quote

import qrcode
from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# -----------------------------
# Simple counters + admin auth
# -----------------------------
COUNTERS_FILE = os.environ.get("COUNTERS_FILE", "counters.json")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me")  # set in Render env vars
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")  # set in Render env vars
app.secret_key = SECRET_KEY

ADMIN_AUTH_FILE = os.environ.get("ADMIN_AUTH_FILE", "admin_auth.json")
ADMIN_RESET_KEY = os.environ.get("ADMIN_RESET_KEY", "")  # set in Render env vars to allow password resets

# -----------------------------
# Multi-card directory
# -----------------------------
CARDS_FILE = os.environ.get("CARDS_FILE", "cards.json")


def load_cards():
    if not os.path.exists(CARDS_FILE):
        raise RuntimeError("cards.json missing")
    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_card(slug: str):
    data = load_cards()
    card = data.get("cards", {}).get(slug)
    if not card:
        return None
    card = dict(card)
    card["slug"] = slug
    return card


def get_default_slug():
    data = load_cards()
    return data.get("default_slug", "wjm")


DEFAULT_COUNTERS = {
    "contact_shared": 0,
    "whatsapp_clicks": 0,
    "email_clicks": 0,
    "map_clicks": 0,
    "share_clicks": 0,
    "nfc_scans": 0,
}


def _save_counters(data: dict):
    tmp = COUNTERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, COUNTERS_FILE)


def _load_counters() -> dict:
    """Load counters from disk.

    Stored shape is {slug: {counter_key: int, ...}, ...}.
    Also supports migrating older flat dicts into the per-slug format.
    """
    if not os.path.exists(COUNTERS_FILE):
        _save_counters({})
        return {}

    try:
        with open(COUNTERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}

        # LEGACY SUPPORT:
        # Older versions stored counters as a single flat dict (not per-slug).
        # If we detect that shape, migrate it under the default slug.
        if any(k in data for k in DEFAULT_COUNTERS.keys()) and not any(
            isinstance(v, dict) for v in data.values()
        ):
            try:
                default_slug = get_default_slug()
            except Exception:
                default_slug = "wjm"
            migrated = {default_slug: {}}
            for k, v in DEFAULT_COUNTERS.items():
                migrated[default_slug][k] = int(data.get(k, v))
            data = migrated
            _save_counters(data)

        return data
    except Exception:
        # If file is corrupted, reset safely
        _save_counters({})
        return {}


def increment_counter(slug: str, key: str) -> int:
    data = _load_counters()
    card_data = data.get(slug, {})
    for k, v in DEFAULT_COUNTERS.items():
        card_data.setdefault(k, v)

    card_data[key] = int(card_data.get(key, 0)) + 1
    data[slug] = card_data
    _save_counters(data)
    return card_data[key]


def get_counters(slug: str) -> dict:
    data = _load_counters()
    card_data = data.get(slug, {})
    for k, v in DEFAULT_COUNTERS.items():
        card_data.setdefault(k, v)
    return card_data


def is_admin_logged_in() -> bool:
    return bool(session.get("admin_logged_in"))


def _load_admin_password_hash() -> str | None:
    """Load persisted admin password hash if present."""
    try:
        if os.path.exists(ADMIN_AUTH_FILE):
            with open(ADMIN_AUTH_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ph = data.get("password_hash")
            if isinstance(ph, str) and ph.strip():
                return ph.strip()
    except Exception:
        # Don't crash app if file is corrupt; fall back to env password
        return None
    return None


def _save_admin_password_hash(password_hash: str) -> None:
    tmp = ADMIN_AUTH_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"password_hash": password_hash}, f, indent=2)
    os.replace(tmp, ADMIN_AUTH_FILE)



def password_ok(pw: str) -> bool:
    # 1) Prefer persisted hash (allows reset without changing Render env vars)
    persisted = _load_admin_password_hash()
    if persisted:
        return check_password_hash(persisted, pw)

    # 2) Fallback to env var (supports either a hash or plain text)
    if ADMIN_PASSWORD.startswith("pbkdf2:") or ADMIN_PASSWORD.startswith("scrypt:"):
        return check_password_hash(ADMIN_PASSWORD, pw)
    return pw == ADMIN_PASSWORD



def build_admin_rows():
    cards_data = load_cards()
    cards = cards_data.get("cards", {})
    all_counters = _load_counters()

    rows = []
    for slug, c in cards.items():
        counters = all_counters.get(slug, {})
        for k, v in DEFAULT_COUNTERS.items():
            counters.setdefault(k, v)

        rows.append(
            {
                "slug": slug,
                "display_name": c.get("display_name", slug),
                "contact_save_name": c.get("contact_save_name", ""),
                "contact_shared": counters.get("contact_shared", 0),
                "whatsapp_clicks": counters.get("whatsapp_clicks", 0),
                "email_clicks": counters.get("email_clicks", 0),
                "map_clicks": counters.get("map_clicks", 0),
                "share_clicks": counters.get("share_clicks", 0),
                "nfc_scans": counters.get("nfc_scans", 0),
                "card_url": f"/c/{slug}",
            }
        )

    rows.sort(key=lambda r: r["slug"])
    return rows

@app.get("/")
def home():
    return redirect(f"/c/{get_default_slug()}", code=302)


@app.get("/wjm")
def digital_card():
    return redirect(f"/c/{get_default_slug()}", code=302)


@app.get("/wjm.vcf")
def vcard():
    return redirect(f"/c/{get_default_slug()}.vcf", code=302)


@app.get("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico")


@app.get("/go/whatsapp/<slug>")
def go_whatsapp(slug):
    c = get_card(slug)
    if not c:
        return abort(404)
    increment_counter(slug, "whatsapp_clicks")
    msg = request.args.get("text", "")
    base = f"https://wa.me/{c['whatsapp_e164']}"
    if msg:
        return redirect(base + "?text=" + quote(msg), code=302)
    return redirect(base, code=302)


@app.get("/go/email/<slug>")
def go_email(slug):
    c = get_card(slug)
    if not c:
        return abort(404)
    increment_counter(slug, "email_clicks")
    subject = request.args.get("subject", "Enquiry from Website")
    return redirect(f"mailto:{c['email']}?subject={quote(subject)}", code=302)


@app.get("/go/map/<slug>")
def go_map(slug):
    c = get_card(slug)
    if not c:
        return abort(404)
    increment_counter(slug, "map_clicks")
    destination = c.get("maps_destination", "208%20Weltevreden%20Road%2C%20Northcliff")
    return redirect(f"https://www.google.com/maps/dir/?api=1&destination={destination}", code=302)


@app.route("/admin", methods=["GET"])
def admin():
    if not is_admin_logged_in():
        return redirect(url_for("admin_login"), code=302)

    rows = build_admin_rows()
    return render_template("admin.html", rows=rows)


@app.get("/admin/export.csv")
def admin_export_csv():
    if not is_admin_logged_in():
        return redirect(url_for("admin_login"), code=302)

    rows = build_admin_rows()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "slug",
        "display_name",
        "contact_save_name",
        "contact_shared",
        "whatsapp_clicks",
        "email_clicks",
        "map_clicks",
        "share_clicks",
        "nfc_scans",
        "card_url",
    ])
    for r in rows:
        writer.writerow([
            r["slug"],
            r["display_name"],
            r["contact_save_name"],
            r["contact_shared"],
            r["whatsapp_clicks"],
            r["email_clicks"],
            r["map_clicks"],
            r["share_clicks"],
            r["nfc_scans"],
            r["card_url"],
        ])

    csv_data = output.getvalue()
    output.close()

    ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=card-stats-{ts}.csv"},
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        if password_ok(pw):
            session["admin_logged_in"] = True
            return redirect(url_for("admin"), code=302)
        return render_template("admin_login.html", error="Incorrect password.")
    return render_template("admin_login.html", error=None)


@app.post("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"), code=302)



@app.route("/admin/password-reset", methods=["GET", "POST"])
def admin_password_reset():
    # This reset flow is protected by a separate environment key.
    # Set ADMIN_RESET_KEY in Render env vars. Keep it private.
    if not ADMIN_RESET_KEY:
        return render_template(
            "admin_password_reset.html",
            error="Password reset is not enabled. Set ADMIN_RESET_KEY in your environment variables.",
            success=None,
        )

    if request.method == "POST":
        reset_key = request.form.get("reset_key", "")
        new_pw = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if reset_key != ADMIN_RESET_KEY:
            return render_template(
                "admin_password_reset.html",
                error="Incorrect reset key.",
                success=None,
            )

        if not new_pw or len(new_pw) < 8:
            return render_template(
                "admin_password_reset.html",
                error="Password must be at least 8 characters.",
                success=None,
            )

        if new_pw != confirm:
            return render_template(
                "admin_password_reset.html",
                error="Passwords do not match.",
                success=None,
            )

        # Persist new password hash so you don't need to change Render env vars.
        _save_admin_password_hash(generate_password_hash(new_pw))
        session.pop("admin_logged_in", None)
        return render_template(
            "admin_password_reset.html",
            error=None,
            success="Password updated. You can now sign in with the new password.",
        )

    return render_template("admin_password_reset.html", error=None, success=None)


@app.post("/admin/reset-counters")
def admin_reset_counters():
    if not is_admin_logged_in():
        return redirect(url_for("admin_login"), code=302)
    _save_counters({})
    return redirect(url_for("admin"), code=302)


@app.get("/qr.png")
def qr_png():
    # Backwards compatible: serve QR for the default card
    return redirect(url_for("qr_png_slug", slug=get_default_slug()), code=302)


@app.get("/qr/<slug>.png")
def qr_png_slug(slug):
    c = get_card(slug)
    if not c:
        return abort(404)
    base_url = request.host_url.rstrip("/")
    url = base_url + "/go/nfc/" + slug  # track scans
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="image/png")


@app.get("/c/<slug>")
def card(slug):
    c = get_card(slug)
    if not c:
        return abort(404)
    counters = get_counters(slug)
    return render_template(
        "card.html",
        share_count=counters.get("contact_shared", 0),
        display_name=c["display_name"],
        contact_save_name=c["contact_save_name"],
        org=c["org"],
        title=c["title"],
        whatsapp_display=c["whatsapp_display"],
        whatsapp_e164=c["whatsapp_e164"],
        office_display=c["office_display"],
        office_e164=c["office_e164"],
        email=c["email"],
        website_display=c["website_display"],
        website_url=c["website_url"],
        address_text=c["address_text"],
        maps_destination=c["maps_destination"],
        photo_filename=c.get("photo_filename", "profile.jpg"),
        logo_filename=c.get("logo_filename", "logo.png"),
        slug=slug,
    )


@app.get("/c/<slug>.vcf")
def vcard_slug(slug):
    c = get_card(slug)
    if not c:
        return abort(404)

    increment_counter(slug, "contact_shared")

    image_path = Path("static") / c.get("photo_filename", "profile.jpg")
    encoded_image = ""
    try:
        encoded_image = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    except Exception:
        encoded_image = ""

    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{c['contact_save_name']}",
        f"ORG:{c['org']}",
        f"TITLE:{c['title']}",
        f"TEL;TYPE=CELL,VOICE:+{c['whatsapp_e164']}",
        f"TEL;TYPE=WORK,VOICE:+{c['office_e164']}",
        f"EMAIL;TYPE=WORK:{c['email']}",
        f"URL:{c['website_url']}",
    ]
    if encoded_image:
        lines.append(f"PHOTO;ENCODING=b;TYPE=JPEG:{encoded_image}")
    lines += ["END:VCARD", ""]

    vcf = "\r\n".join(lines)

    safe_name = slug.replace("/", "_")
    return Response(
        vcf,
        mimetype="text/vcard; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={safe_name}.vcf",
            "Cache-Control": "no-store",
        },
    )


@app.get("/go/share/<slug>")

def go_share(slug):
    c = get_card(slug)
    if not c:
        return abort(404)
    increment_counter(slug, "share_clicks")
    return ("", 204)


@app.get("/go/nfc/<slug>")
def go_nfc(slug):
    c = get_card(slug)
    if not c:
        return abort(404)
    increment_counter(slug, "nfc_scans")
    return redirect(url_for("card", slug=slug))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)