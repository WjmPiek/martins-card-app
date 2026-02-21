UPDATE: SHARE CONTACT OPTIONS (NFC vs Contact File)

- The "Share Contact" button now opens a popup with 2 choices:
  1) Share via NFC  -> opens /go/nfc/<slug>
  2) Share Contact File -> shares /c/<slug>.vcf via native share sheet (fallback downloads)

NOTE:
- Phones cannot transmit NFC programmatically from a website.
  "Share via NFC" opens the NFC flow URL so the user can proceed via the NFC tag/URL.
