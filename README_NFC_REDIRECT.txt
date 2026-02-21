NFC + CONTACT SAVE + PROFILE REDIRECT (iPhone-friendly)

What happens when someone taps NFC:
1) /go/nfc/<slug> increments nfc_scans
2) Shows a small "Save Contact" page that auto-opens /c/<slug>.vcf once
3) After the user saves and taps Back, the page auto-redirects them to /c/<slug>

Why:
- iOS shows the contact viewer for .vcf files and does not allow JS redirects from within that viewer.
- This approach redirects as soon as the user returns from the contact viewer.

Install:
- Put nfc_save.html into your Flask templates/ folder as templates/nfc_save.html
