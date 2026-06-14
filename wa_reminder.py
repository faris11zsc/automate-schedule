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

import os, requests, pytz, smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
import email.utils

NOTION_TOKEN   = os.environ.get("NOTION_TOKEN")
GMAIL_ADDRESS  = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
DATABASE_ID    = "5cb27942-1b67-4dc6-9de4-e9e72dafbbea"
WINDOW         = (5, 60)   # send when session is this many minutes away
DEDUP_HOURS    = 18         # safety net: never re-send within this window

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
        current_next_str = get_date(p.get("next session Date",{}))

        print(f"── {name}")

        if not email_addr:
            print("   skip: no email address"); continue

        sessions = parse_schedule(sch, tz_s)

        # ── SYNC: Update 'Next Session' property for Notion Calendar ──
        actual_next = None
        nxt_base = next_recurring_utc(sessions, now)
        
        if override_date:
            try:
                raw_odt = datetime.fromisoformat(override_date.replace("Z","+00:00"))
                odt = pytz.timezone(norm_tz(tz_s)).localize(raw_odt.replace(tzinfo=None))
                if now <= odt + timedelta(hours=1):
                    actual_next = odt
            except: pass
            
        if not actual_next and nxt_base:
            if skip_next:
                actual_next = next_recurring_utc(sessions, nxt_base + timedelta(hours=2))
            else:
                actual_next = nxt_base
                
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
                print(f"   📅 Calendar synced (Egypt Time): {cairo_dt.strftime('%b %d, %I:%M %p')}")
        elif current_next_str:
            notion_update(rid, [{"name":"next session Date","type":"date","value":None}])
            print(f"   📅 Calendar cleared")

        # ── CASE 1: Skip Next ✅ ──────────────────────────────────
        if skip_next:
            if not skip_until:
                # First detection — record which session is being cancelled
                if nxt_base:
                    notion_update(rid, [{"name":"Skip Until","type":"date","value":to_iso(nxt_base)}])
                    print(f"   Skip Next ✅ — cancelling session at {fmt(nxt_base, tz_s)}, will auto-clear after")
                else:
                    print("   Skip Next ✅ — no schedule to reference")
            else:
                skip_until_dt = datetime.fromisoformat(skip_until.replace("Z","+00:00"))
                if now > skip_until_dt + timedelta(minutes=30):
                    # Cancelled session has passed → auto-clear both fields
                    notion_update(rid, [
                        {"name": "Skip Next",  "type": "checkbox", "value": "False"},
                        {"name": "Skip Until", "type": "date",     "value": None}
                    ])
                    print(f"   ↩ Cancelled session passed — Skip Next & Skip Until auto-cleared")
                else:
                    print(f"   Skip Next ✅ — session at {fmt(skip_until_dt, tz_s)} not yet passed, holding")
            continue

        # ── CASE 2: Override Time set → one-time reschedule ───────
        if override_date:
            try:
                raw_odt = datetime.fromisoformat(override_date.replace("Z","+00:00"))
                override_dt = pytz.timezone(norm_tz(tz_s)).localize(raw_odt.replace(tzinfo=None))
                if now > override_dt + timedelta(hours=1):
                    # Override has passed → auto-clear
                    notion_update(rid, [{"name":"Override Time","type":"date","value":None}])
                    print("   Override Time passed — auto-cleared, falling through to schedule")
                    # Fall through to normal schedule below
                else:
                    mins = (override_dt - now).total_seconds() / 60
                    print(f"   Override → {fmt(override_dt, tz_s)} ({mins:.0f} min away)")
                    if WINDOW[0] <= mins <= WINDOW[1]:
                        if already_sent(lr, override_dt):
                            print("   already reminded")
                        else:
                            _send(rid, name, email_addr, override_dt, tz_s, now)
                            notion_update(rid, [{"name":"Override Time","type":"date","value":None}])
                    else:
                        print("   not in window")
                    continue
            except Exception as e:
                print(f"   Override Time error: {e} — using recurring schedule")

        # ── CASE 3: Normal recurring schedule ─────────────────────
        if not nxt_base:
            print("   skip: no parseable schedule"); continue

        mins = (nxt_base - now).total_seconds() / 60
        print(f"   Recurring → {fmt(nxt_base, tz_s)} ({mins:.0f} min away)")

        if not (WINDOW[0] <= mins <= WINDOW[1]):
            print("   not in window"); continue
        if already_sent(lr, nxt_base):
            print("   already reminded"); continue

        _send(rid, name, email_addr, nxt_base, tz_s, now)
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
