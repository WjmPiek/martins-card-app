from __future__ import annotations

import base64
from pathlib import Path

from flask import Flask, Response, render_template, redirect, send_from_directory

app = Flask(__name__)


@app.get("/")
def home():
    return redirect("/wjm", code=302)


@app.get("/wjm")
def digital_card():
    """Premium digital business card page."""
    return render_template(
        "card.html",
        display_name="Wjm Piek",
        org="Martin’s Funerals",
        title="Director",
        whatsapp_display="082 561 5932",
        whatsapp_e164="27825615932",
        office_display="010 448 0921",
        office_e164="27104480921",
        email="wjm@martinsdirect.com",
        website_display="martinsnorthcliff.com",
        website_url="https://www.martinsnorthcliff.com",
        address_display="208 Weltevreden Road, Northcliff",
        maps_destination="208%20Weltevreden%20Road%2C%20Northcliff",
    )


@app.get("/wjm.vcf")
def vcard():
    """
    vCard download that saves to iPhone & Android contacts (with embedded photo).
    Place the image at: static/profile.jpg
    """
    image_path = Path(app.static_folder) / "profile.jpg"
    encoded_image = ""
    if image_path.exists():
        encoded_image = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    # vCard 3.0 works broadly; CRLF line endings are important.
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        "N:Funerals;Wjm;;;",
        "FN:Wjm Martin’s Funerals",
        "ORG:Martin’s Funerals",
        "TITLE:Director",
        "TEL;TYPE=CELL,VOICE:+27825615932",
        "TEL;TYPE=WORK,VOICE:+27104480921",
        "EMAIL;TYPE=WORK:wjm@martinsdirect.com",
        "URL:https://www.martinsnorthcliff.com",
        "ADR;TYPE=WORK:;;208 Weltevreden Road;Northcliff;;;South Africa",
    ]
    if encoded_image:
        lines.append(f"PHOTO;ENCODING=b;TYPE=JPEG:{encoded_image}")
    lines += [
        "NOTE:Professional Funeral & Cremation Services",
        "END:VCARD",
        "",
    ]
    vcf = "\r\n".join(lines)

    return Response(
        vcf,
        mimetype="text/vcard; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=wjm_martins_funerals.vcf",
            "Cache-Control": "no-store",
        },
    )




@app.get("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico")


if __name__ == "__main__":
    app.run(debug=True)
