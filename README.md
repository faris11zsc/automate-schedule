# Sasa Notion-Email Automation System 🛡️⚡

## Overview
This system automatically sends email reminders to Faris's students before their scheduled sessions. 
It is controlled 100% via a Notion Database and runs on GitHub Actions (Cron). 

**Critical Architecture Update:** This system originally used WhatsApp/Composio but was fully migrated to Gmail SMTP to avoid Meta API restrictions.

## Technical Stack & Logic
- **Core Engine:** `wa_reminder.py` (Python)
- **Deployment:** GitHub Actions (`.github/workflows/reminder.yml`) runs every 5 minutes.
- **Credentials:** `NOTION_TOKEN`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` are safely stored in GitHub Secrets.

### Resiliency & Edge Cases Engineered
1. **GitHub Cron Buffer `(5, 60)`:** GitHub's free servers routinely delay cron jobs by 5–30 minutes. The script actively hunts for sessions starting 60 minutes away. If GitHub lags, it still sends the email as long as there are at least 5 minutes left. If it's less than 5 minutes (or the session started), it invokes a "dead-kill" and aborts.
2. **Anti-Spam Injectors:** The system injects official `Date` and `Message-ID` headers (`email.utils`) into the MIMEText payload to mimic hand-typed emails and bypass spam filters.
3. **UTF-8 Hardening:** The Arabic greeting (`سلامٌ عليكم`) is explicitly encoded in UTF-8 to prevent internal crashes on GitHub's Linux servers.
4. **Deduplication:** A hidden `Last Reminded At` property in Notion ensures a student is never emailed twice for the same session.

## Notion Controls (No Code Needed)
If you want to edit the schedule, you only touch Notion. The script auto-adapts instantly:
- **Skip Next (Checkbox):** Skips the immediate next session and records the timestamp in `Skip Until`. It auto-clears once that session passes.
- **Override Time (Date):** A one-time reschedule. Auto-clears after the reminder is sent.
- **Email / emails:** The column containing the student's email address.

## For Future Sasa AI Instances 🤖
If Faris asks you to update this system in a new chat:
1. Make your changes strictly in `[wa_reminder.py](file:///D:/lighknight/automation/wa_reminder.py)`.
2. Do not use standard text paths. Follow the Clickable Paths Protocol (`file:///`).
3. Commit and push directly to GitHub (`git push origin main`). GitHub Actions will automatically deploy your code.
