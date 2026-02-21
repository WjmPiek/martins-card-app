UPDATE SUMMARY

1) Button change
   - "Save to Contacts" is now "Share Contact" on the card page.
   - It shares the .vcf via the native share sheet (fallback: open/download the .vcf).

2) NFC behaviour (Option B)
   - NFC now redirects directly to the contact file:
     /go/nfc/<slug>  -> increments nfc_scans -> redirects to /c/<slug>.vcf

NFC PROGRAMMING
- Program the NFC tag with the full URL:
  https://<your-domain>/go/nfc/<slug>
