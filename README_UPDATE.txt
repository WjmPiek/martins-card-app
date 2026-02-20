UPDATED FILES

This zip includes:
- Fixed Python syntax/indentation in `_load_counters()` and hardened URL encoding.
- Added proper `templates/` folder structure so Flask can find HTML templates.
- Fixed card template variables (`address_text`), slug-specific vCard saving, and slug-specific QR image route.

Deploy:
```bash
git add .
git commit -m "Fix counters loading + templates structure"
git push
```

Render will auto-deploy automatically.
