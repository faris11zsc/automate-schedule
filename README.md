# Automated WhatsApp Scheduler

## Overview
This project is an automated WhatsApp reminder system built for Faris. It connects a Notion Database to WhatsApp via the Composio API.
It is scheduled to run every 5 minutes using GitHub Actions.

## Key Files
- `wa_reminder.py`: The core Python script that contains all the logic.
- `.github/workflows/reminder.yml`: The GitHub Actions configuration that triggers the script every 5 minutes.
- `requirements.txt`: Python dependencies (`requests`, `pytz`).

## How it works
1. GitHub Actions runs `wa_reminder.py` every 5 minutes.
2. The script queries a specific Notion database looking for students with `Status = Active`.
3. It calculates the next session time based on the student's `schadule` and `Timezone` properties.
4. If a session is exactly 28 to 32 minutes away, it triggers the Composio `WHATSAPP_SEND_MESSAGE` action to send a reminder.
5. It prevents duplicate messages using a hidden `Last Reminded At` property in Notion.

## Notion Columns & System Logic
If an AI needs to modify this, be aware of these specific Notion columns:
- **Skip Next (Checkbox)**: If checked, the script skips the immediate next session. It writes the cancelled session's timestamp to `Skip Until`. Once that time passes, the script *auto-clears* the checkbox and `Skip Until` date.
- **Override Time (Date)**: Used for one-off reschedules. The script will use this time instead of the regular schedule. It *auto-clears* after the reminder is sent.
- **schadule (Text)**: Format is `Days, Times` (e.g., `mo,we,fr 12:00,14:00,16:00`).

## For Future AI Assistants
If Faris asks you to update this system:
1. Make your code changes in `wa_reminder.py`.
2. Commit and push the changes to `https://github.com/faris11zsc/automate-schedule` using the terminal so GitHub Actions picks up the new code.
3. The `COMPOSIO_API_KEY` is stored in GitHub Secrets, not locally.
