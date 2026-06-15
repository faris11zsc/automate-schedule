#!/usr/bin/env python3
"""
WhatsApp Session Reminder — GitHub Actions, runs every 5 minutes.
Needs: COMPOSIO_API_KEY as a GitHub secret.

HOW TO CONTROL (everything in Notion, nothing else needed):
  Status       Paused / Inactive  → no reminders
  Skip Next    ✅ check           → cancels next session; auto-clears after it passes
  Override Time  pick a date      → one-time reschedule; auto-clears after it passes
  Everything else (schedule, timezone, number) → just edit in Notion, picked up instantly
"""

import os, sys, time, json
import requests
import pytz
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
import smtplib
import email.utils

# ── Google Calendar Dependencies ──
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    service_account = None

NOTION_TOKEN   = os.environ.get("NOTION_TOKEN")
GMAIL_ADDRESS  = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
DATABASE_ID    = "5cb27942-1b67-4dc6-9de4-e9e72dafbbea"
WINDOW         = (5, 60)   # send when session is this many minutes away
DEDUP_HOURS    = 2         # safety net: never re-send within this window

# ── Google Calendar Setup ─────────────────────────────────────────────
GCAL_CALENDAR_ID = "843564b811e67948fe8e1125a241fc60a08a9698837f4735cba8196e50e44e4a@group.calendar.google.com"
GCAL_CREDS_JSON  = os.environ.get("GCAL_CREDENTIALS")

gcal_service = None
if GCAL_CREDS_JSON and service_account:
    try:
        creds_info = json.loads(GCAL_CREDS_JSON)
        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/calendar']
        )
        gcal_service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        print(f"Failed to init GCal: {e}")

def sync_gcal(event_id, summary, start_dt):
    if not gcal_service: return
    
    cairo_tz = pytz.timezone("Africa/Cairo")
    start_cairo = start_dt.astimezone(cairo_tz)
    end_cairo = start_cairo + timedelta(minutes=60)
    
    event_body = {
        'id': event_id,
        'summary': summary,
        'start': {
            'dateTime': start_cairo.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'Africa/Cairo'
        },
        'end': {
            'dateTime': end_cairo.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'Africa/Cairo'
        },
    }
    try:
        gcal_service.events().update(calendarId=GCAL_CALENDAR_ID, eventId=event_id, body=event_body).execute()
    except Exception as e:
        if "404" in str(e):
            try:
                gcal_service.events().insert(calendarId=GCAL_CALENDAR_ID, body=event_body).execute()
            except: pass
        else: pass

def delete_gcal(event_id):
    if not gcal_service: return
    try:
        gcal_service.events().delete(calendarId=GCAL_CALENDAR_ID, eventId=event_id).execute()
    except: pass

# ── Direct APIs ───────────────────────────────────────────────────────
def notion_query_database():
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "filter": {"property": "Status", "select": {"equals": "Active"}},
        "page_size": 100
    }
    
    results = []
    has_more = True
    
    while has_more:
        r = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers, json=data, timeout=30)
        r.raise_for_status()
        resp = r.json()
        results.extend(resp.get("results", []))
        has_more = resp.get("has_more", False)
        if has_more:
            data["start_cursor"] = resp.get("next_cursor")
            
    return {"results": results}

def notion_update(row_id, props):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    properties = {}
    for p in props:
        name, ptype, val = p["name"], p["type"], p["value"]
        if ptype == "checkbox":
            properties[name] = {"checkbox": True if val == "True" else False}
        elif ptype == "date":
            if isinstance(val, dict):
                properties[name] = {"date": val}
            else:
                properties[name] = {"date": {"start": val} if val else None}
            
    r = requests.patch(f"https://api.notion.com/v1/pages/{row_id}", headers=headers, json={"properties": properties}, timeout=30)
    r.raise_for_status()

# ── Timezone ──────────────────────────────────────────────────────────
TZ_ALIAS = {
    "london":"Europe/London","est":"America/New_York","et":"America/New_York",
    "pst":"America/Los_Angeles","cairo":"Africa/Cairo","dubai":"Asia/Dubai",
    "gmt":"UTC","utc":"UTC",
}
def norm_tz(s):
    if not s: return "UTC"
    k = s.strip().lower()
    if k in TZ_ALIAS: return TZ_ALIAS[k]
    try: pytz.timezone(s.strip()); return s.strip()
    except: return "UTC"

def fmt(dt, tz_s):
    try: return dt.astimezone(pytz.timezone(norm_tz(tz_s))).strftime("%I:%M %p")
    except: return dt.strftime("%H:%M UTC")

def to_iso(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

# ── Schedule parser ───────────────────────────────────────────────────
DAYS = {"mo":0,"mon":0,"tu":1,"tue":1,"we":2,"wed":2,"th":3,"thu":3,
        "fr":4,"fri":4,"sa":5,"sat":5,"su":6,"sun":6,"sum":6}

def parse_time_str(s):
    s = s.strip().lower()
    pm, am = "pm" in s, "am" in s
    s = s.replace("pm","").replace("am","").strip()
    if ":" in s: h, m = int(s.split(":")[0]), int(s.split(":")[1])
    else: h = int(s) if s.isdigit() else 12; m = 0
    if pm and h < 12: h += 12
    elif am and h == 12: h = 0
    elif not am and not pm and 1 <= h <= 11: h += 12
    return h, m

import re

def parse_schedule(sch, tz_s):
    if not sch or not sch.strip(): return []
    sch = sch.strip().lower()
    
    # Extract all valid day abbreviations
    day_matches = re.findall(r'[a-z]+', sch)
    days = []
    for d in day_matches:
        if d in ('am', 'pm'): continue
        if d[:3] in DAYS: days.append(d[:3])
        elif d[:2] in DAYS: days.append(d[:2])
    
    # Extract all time patterns (e.g. 1, 1:00, 1 am, 1 : 00pm)
    time_matches = re.findall(r'\d{1,2}(?:\s*:\s*\d{2})?(?:\s*[ap]m)?', sch)
    times = [t.strip() for t in time_matches]
    
    if not days or not times: return []
    
    tz_n  = norm_tz(tz_s)
    out   = []
    for i, d in enumerate(days):
        wd = DAYS[d]
        t = times[i] if i < len(times) else times[-1]
        try: h, m = parse_time_str(t); out.append((wd, h, m, tz_n))
        except: pass
    return out

def next_recurring_utc(sessions, now):
    best = None
    for wd, h, m, tz_n in sessions:
        try:
            tz  = pytz.timezone(tz_n)
            loc = now.astimezone(tz)
            d   = (wd - loc.weekday()) % 7
            c   = (loc + timedelta(days=d)).replace(hour=h, minute=m, second=0, microsecond=0)
            if c <= loc - timedelta(hours=2): c += timedelta(days=7)
            u = c.astimezone(pytz.utc)
            if best is None or u < best: best = u
        except: pass
    return best

# ── Notion helpers ────────────────────────────────────────────────────
def txt(prop, kind):
    return "".join(t.get("plain_text","") for t in prop.get(kind,[]))

def get_date(prop):
    return ((prop or {}).get("date") or {}).get("start")

def already_sent(last_str, session_dt):
    if not last_str: return False
    try:
        last = datetime.fromisoformat(last_str.replace("Z","+00:00"))
        return abs((session_dt - last).total_seconds()) / 3600 < DEDUP_HOURS
    except: return False

# ── Main ──────────────────────────────────────────────────────────────
def run():
    now  = datetime.now(timezone.utc)
    try:
        data = notion_query_database()
        rows = data.get("results", [])
    except Exception as e:
        print(f"Failed to fetch Notion Database: {e}")
        return
    print(f"{now.strftime('%a %Y-%m-%d %H:%M UTC')} — {len(rows)} active students\n")

    for row in rows:
        p    = row.get("properties", {})
        rid  = row["id"]
        name = txt(p.get("Student Name",{}), "title")
        sch  = txt(p.get("schadule",{}),     "rich_text")
        tz_s = txt(p.get("Timezone",{}),     "rich_text")
        em_prop = p.get("Email") or p.get("emails") or {}
        email_addr = em_prop.get("email") or txt(em_prop, "rich_text")
        lr   = get_date(p.get("Last Reminded At",{}))

        skip_next     = p.get("Skip Next",{}).get("checkbox", False)
        skip_until    = get_date(p.get("Skip Until",{}))
        override_date = get_date(p.get("Override Time",{}))
        extra_date    = get_date(p.get("extra session",{}))
        current_next_str = get_date(p.get("next session Date",{}))

        print(f"── {name}")

        if not email_addr:
            print("   skip: no email address"); continue

        sessions = parse_schedule(sch, tz_s)
        nxt_base = next_recurring_utc(sessions, now)

        # ── Handle Skip Next auto-clearing First ──
        if skip_next:
            if not skip_until:
                if nxt_base:
                    notion_update(rid, [{"name":"Skip Until","type":"date","value":to_iso(nxt_base)}])
                    print(f"   Skip Next ✅ — cancelling session at {fmt(nxt_base, tz_s)}, will auto-clear after")
            else:
                skip_until_dt = datetime.fromisoformat(skip_until.replace("Z","+00:00"))
                if now > skip_until_dt + timedelta(minutes=30):
                    notion_update(rid, [
                        {"name": "Skip Next",  "type": "checkbox", "value": "False"},
                        {"name": "Skip Until", "type": "date",     "value": None}
                    ])
                    print(f"   ↩ Cancelled session passed — Skip auto-cleared")
                    skip_next = False

        candidates = []

        # 1. Extra Session (lives alongside everything)
        if extra_date:
            try:
                raw_extra = datetime.fromisoformat(extra_date.replace("Z","+00:00"))
                edt = pytz.timezone(norm_tz(tz_s)).localize(raw_extra.replace(tzinfo=None))
                if now > edt + timedelta(hours=1):
                    notion_update(rid, [{"name":"extra session","type":"date","value":None}])
                    print("   Extra Session passed — auto-cleared")
                else:
                    candidates.append(("Extra", edt))
            except: pass

        # 2. Main Schedule (Override replaces Recurring)
        has_active_override = False
        if override_date:
            try:
                raw_odt = datetime.fromisoformat(override_date.replace("Z","+00:00"))
                odt = pytz.timezone(norm_tz(tz_s)).localize(raw_odt.replace(tzinfo=None))
                if now > odt + timedelta(hours=1):
                    notion_update(rid, [{"name":"Override Time","type":"date","value":None}])
                    print("   Override Time passed — auto-cleared")
                else:
                    candidates.append(("Override", odt))
                    has_active_override = True
            except: pass

        # 3. Recurring Schedule
        if not has_active_override and nxt_base:
            if skip_next:
                after_skip = next_recurring_utc(sessions, nxt_base + timedelta(hours=2))
                if after_skip:
                    candidates.append(("Recurring", after_skip))
            else:
                candidates.append(("Recurring", nxt_base))

        # Sort all upcoming valid sessions by time to find the absolute closest one
        candidates.sort(key=lambda x: x[1])
        actual_next = candidates[0][1] if candidates else None

        # ── SYNC: Update 'next session Date' property for Notion Calendar ──
        event_id = rid.replace("-", "")
        if actual_next:
            cairo_dt = actual_next.astimezone(pytz.timezone("Africa/Cairo"))
            cairo_str = cairo_dt.strftime("%Y-%m-%dT%H:%M:%S")
            
            needs_update = True
            if current_next_str:
                try:
                    c_dt = datetime.fromisoformat(current_next_str.replace("Z","+00:00"))
                    if abs((c_dt - actual_next).total_seconds()) < 60:
                        needs_update = False
                except: pass
                
            if needs_update:
                notion_update(rid, [{"name":"next session Date","type":"date",
                                     "value":{"start": cairo_str, "time_zone": "Africa/Cairo"}}])
                print(f"   📅 Notion Calendar synced (Egypt Time): {cairo_dt.strftime('%b %d, %I:%M %p')}")
                sync_gcal(event_id, name, actual_next)
                print(f"   📅 Google Calendar synced")
        elif current_next_str:
            notion_update(rid, [{"name":"next session Date","type":"date","value":None}])
            print(f"   📅 Calendars cleared")
            delete_gcal(event_id)

        # ── CHECK FOR NOTIFICATIONS ──
        notified = False
        for kind, dt_cand in candidates:
            mins = (dt_cand - now).total_seconds() / 60
            if WINDOW[0] <= mins <= WINDOW[1]:
                print(f"   {kind} → {fmt(dt_cand, tz_s)} ({mins:.0f} min away)")
                if already_sent(lr, dt_cand):
                    print("   already reminded")
                else:
                    _send(rid, name, email_addr, dt_cand, tz_s, now)
                notified = True
                break

        if not notified and candidates:
            kind, dt_cand = candidates[0]
            mins = (dt_cand - now).total_seconds() / 60
            print(f"   Next is {kind} → {fmt(dt_cand, tz_s)} ({mins:.0f} min away) [Not in window]")
        
        print()

def _send(row_id, name, email_addr, session_dt, tz_s, now):
    msg_text = f"سلامٌ عليكم {name},\n\nYour session starts soon at {fmt(session_dt, tz_s)}.\n\nSee you soon!\n\nBest,\nFaris\n\n\n\nThis message is automated"
    msg = MIMEText(msg_text, 'plain', 'utf-8')
    msg['Subject'] = 'Upcoming Session Reminder'
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = email_addr
    msg['Date'] = email.utils.formatdate(localtime=False)
    msg['Message-ID'] = email.utils.make_msgid()
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
            
        notion_update(row_id, [{"name":"Last Reminded At","type":"date","value":to_iso(now)}])
        print(f"   ✓ Sent to {name} ({email_addr})")
    except Exception as e:
        print(f"   ✗ Failed for {name}: {e}")

run()
