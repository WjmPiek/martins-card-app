# Martins Northcliff Digital Card (Flask)

## Folder layout
- app.py
- requirements.txt
- cards.json
- counters.json
- templates/
  - card.html
  - admin.html
  - admin_login.html
- static/
  - logo.png
  - profile.jpg

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000/

## Key endpoints
- `/` -> redirects to the default card (from `cards.json`)
- `/c/<slug>` -> card page
- `/c/<slug>.vcf` -> Save-to-Contacts vCard
- `/go/nfc/<slug>` -> tracked open (use for QR / NFC scans)
- `/qr/<slug>.png` -> QR image for a specific card (tracked)
- `/admin` -> admin dashboard (password protected)
- `/admin/export.csv` -> export counters to CSV
