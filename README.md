# Martins Northcliff Digital Card (Flask)

## Folder layout
- app.py
- requirements.txt
- templates/
  - card.html
- static/
  - logo.png
  - profile.jpg

## Run locally
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py

Open: http://127.0.0.1:5000/wjm

## Endpoints
- /wjm      -> digital business card
- /wjm.vcf  -> Save-to-Contacts vCard (includes avatar from static/profile.jpg)


## Multiple cards

Edit `cards.json` to add more cards.

Each card:
- `/c/<slug>` (card)
- `/c/<slug>.vcf` (save contact)

Homepage `/` redirects to the default card.
