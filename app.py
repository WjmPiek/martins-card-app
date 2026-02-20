from __future__ import annotations

import base64
import os
import json
import qrcode
import io
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from flask import Flask, Response, abort, redirect, render_template, request, send_from_directory, session, url_for

app = Flask(__name__)

# -----------------------------
# Simple counters + admin auth
# -----------------------------

COUNTERS_FILE = os.environ.get("COUNTERS_FILE", "counters.json")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me")  # set in Render env vars
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")  # set in Render env vars

app.secret_key = SECRET_KEY

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
    "share_clicks": 0
}

def _load_counters():
    if not os.path.exists(COUNTERS_FILE):
        _save_counters({})
        return {}
    try:
        with open(COUNTERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
        return data
    except Exception:
        _save_counters({})
        return {}
    except Exception:
        # If file is corrupted, reset safely
        _save_counters(DEFAULT_COUNTERS.copy())
        return DEFAULT_COUNTERS.copy()

def _save_counters(data):
    tmp = COUNTERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, COUNTERS_FILE)


def increment_counter(slug: str, key: str):
    data = _load_counters()
    card_data = data.get(slug, {})
    for k, v in DEFAULT_COUNTERS.items():
        card_data.setdefault(k, v)
    card_data[key] = int(card_data.get(key, 0)) + 1
    data[slug] = card_data
    _save_counters(data)
    return card_data[key]

def get_counters(slug: str):
    data = _load_counters()
    card_data = data.get(slug, {})
    for k, v in DEFAULT_COUNTERS.items():
        card_data.setdefault(k, v)
    return card_data

def is_admin_logged_in():
    return bool(session.get("admin_logged_in"))

def password_ok(pw: str) -> bool:
    # Support both plain-text and hashed password in ADMIN_PASSWORD
    if ADMIN_PASSWORD.startswith("pbkdf2:") or ADMIN_PASSWORD.startswith("scrypt:"):
        return check_password_hash(ADMIN_PASSWORD, pw)
    return pw == ADMIN_PASSWORD


    count = get_share_count() + 1
    with open(COUNTER_FILE, "w") as f:
        f.write(str(count))
    return count



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
        return redirect(base + "?text=" + msg, code=302)
    return redirect(base, code=302)


@app.get("/go/email/<slug>")
def go_email(slug):
    c = get_card(slug)
    if not c:
        return abort(404)
    increment_counter(slug, "email_clicks")
    subject = request.args.get("subject", "Enquiry from Website")
    return redirect(f"mailto:{c['email']}?subject={subject}", code=302)


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

    cards_data = load_cards()
    cards = cards_data.get("cards", {})
    all_counters = _load_counters()

    rows = []
    for slug, c in cards.items():
        counters = all_counters.get(slug, {})
        for k, v in DEFAULT_COUNTERS.items():
            counters.setdefault(k, v)
        rows.append({
            "slug": slug,
            "display_name": c.get("display_name", slug),
            "contact_save_name": c.get("contact_save_name", ""),
            "contact_shared": counters.get("contact_shared", 0),
            "whatsapp_clicks": counters.get("whatsapp_clicks", 0),
            "email_clicks": counters.get("email_clicks", 0),
            "map_clicks": counters.get("map_clicks", 0),
            "card_url": f"/c/{slug}"
        })

    rows.sort(key=lambda r: r["slug"])
    return render_template("admin.html", rows=rows)


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


@app.post("/admin/reset")
def admin_reset():
    if not is_admin_logged_in():
        return redirect(url_for("admin_login"), code=302)
    _save_counters({})
    return redirect(url_for("admin"), code=302)



@app.get("/qr.png")
def qr_png():
    # QR encodes the primary URL (the / route redirects to /wjm)
    base_url = request.host_url.rstrip("/")
    url = base_url + "/"
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
        slug=slug
    )

@app.get("/c/<slug>.vcf")
def vcard_slug(slug):
    c = get_card(slug)
    if not c:
        return abort(404)

    increment_counter(slug, "contact_shared")

    image_path = Path("static") / c.get("photo_filename", "profile.jpg")
    encoded_image = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    vcf = "\r\n".join([
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{c['contact_save_name']}",
        f"ORG:{c['org']}",
        f"TITLE:{c['title']}",
        f"TEL;TYPE=CELL,VOICE:+{c['whatsapp_e164']}",
        f"TEL;TYPE=WORK,VOICE:+{c['office_e164']}",
        f"EMAIL;TYPE=WORK:{c['email']}",
        f"URL:{c['website_url']}",
        f"PHOTO;ENCODING=b;TYPE=JPEG:{encoded_image}",
        "END:VCARD",
        ""
    ])

    safe_name = slug.replace("/", "_")
    return Response(
        vcf,
        mimetype="text/vcard; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={safe_name}.vcf",
            "Cache-Control": "no-store"
        }
    )

@app.get("/go/share/<slug>")
def go_share(slug):
    c = get_card(slug)
    if not c:
        return abort(404)
    increment_counter(slug, "share_clicks")
    return ("", 204)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
