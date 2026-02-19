from flask import Flask, render_template, Response, redirect, send_from_directory
import base64
from pathlib import Path

app = Flask(__name__)

@app.get("/")
def home():
    return redirect("/wjm", code=302)

@app.get("/wjm")
def digital_card():
    return render_template("card.html")

@app.get("/wjm.vcf")
def vcard():
    image_path = Path("static/profile.jpg")
    encoded_image = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    vcf = "\r\n".join([
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
        f"PHOTO;ENCODING=b;TYPE=JPEG:{encoded_image}",
        "NOTE:Professional Funeral & Cremation Services",
        "END:VCARD",
        ""
    ])

    return Response(
        vcf,
        mimetype="text/vcard; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=wjm_martins_funerals.vcf",
            "Cache-Control": "no-store"
        }
    )

@app.get("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico")

if __name__ == "__main__":
    app.run(debug=True)
