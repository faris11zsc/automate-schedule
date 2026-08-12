#!/usr/bin/env python3
"""
KeepTheFlow Email Notifier v2 (rebuilt from scratch)
=====================================================
Uses requests + Supabase REST API directly (no supabase Python package).
Same email engine as wa_reminder.py (which works on GitHub Actions).

Three triggers:
  1. New student registers -> Admin gets notified
  2. Student records instances -> Admin gets notified with deep links
  3. Admin gives feedback -> Student gets notified with deep links
"""

import os
import sys
import json
import smtplib
import email.utils
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

# -- Config --
GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
ADMIN_EMAIL        = "lightknightf1@gmail.com"

SB_URL = os.environ.get("SUPABASE_URL") or "https://lhebavvnrwqojbhyodwc.supabase.co"
SB_KEY = os.environ.get("SUPABASE_KEY") or "sb_publishable_JW75ayCf5SbvyT-02GmjNQ_vFpivPTU"
SB_HEADERS = {
    "apikey": SB_KEY,
    "Authorization": f"Bearer {SB_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

PORTAL = "https://keep-the-flow.vercel.app"
LESSON_PATHS = {
    "idgham_yw_lesson": "lessons/idgham-yw-5-12",
    "qrasm_iqlab_ikhfa": "lessons/iqlab-ikhfa-shafawi",
    "qrasm_idgham_yw": "lessons/idgham-yw",
    "extended_humming": "lessons/extended-humming",
}


# ======= SUPABASE REST HELPERS =======

def sb_get(table, params=""):
    """GET rows from a Supabase table."""
    url = f"{SB_URL}/rest/v1/{table}?{params}"
    r = requests.get(url, headers=SB_HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()

def sb_insert(table, data):
    """INSERT a row into a Supabase table."""
    url = f"{SB_URL}/rest/v1/{table}"
    r = requests.post(url, headers=SB_HEADERS, json=data, timeout=15)
    r.raise_for_status()
    return r.json()

def sb_delete(table, params):
    """DELETE rows from a Supabase table."""
    url = f"{SB_URL}/rest/v1/{table}?{params}"
    r = requests.delete(url, headers=SB_HEADERS, timeout=15)
    r.raise_for_status()


# ======= EMAIL ENGINE (same as wa_reminder.py) =======

def send_email(to_email, to_name, subject, html_body, text_body):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print(f"   [SKIP] No Gmail credentials - cannot send to {to_email}")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"Faris Oransa <{GMAIL_ADDRESS}>"
    msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
    msg['Reply-To'] = GMAIL_ADDRESS
    msg['Date'] = email.utils.formatdate(localtime=False)

    # Domain-aligned Message-ID (prevents Yahoo/iCloud hostname flagging)
    domain = GMAIL_ADDRESS.split('@')[1] if '@' in GMAIL_ADDRESS else 'gmail.com'
    msg['Message-ID'] = email.utils.make_msgid(domain=domain)

    # Plain text FIRST, HTML LAST (per RFC)
    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"   [OK] Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"   [FAIL] Email to {to_email}: {e}")
        return False


# ======= EMAIL TEMPLATES =======

def email_header():
    return """<tr><td style="background:linear-gradient(135deg,#1a2744,#2a3a5e);padding:28px 32px;text-align:center;">
      <h1 style="margin:0;font-size:22px;font-weight:700;color:#c5a44e;letter-spacing:0.5px;">\u2726 Keep The Flow</h1>
    </td></tr>"""

def email_footer():
    return """<tr><td style="background-color:#1a2744;padding:24px 32px;text-align:center;">
      <p style="margin:0;font-size:13px;color:#a0aec0;">Automated notification from KeepTheFlow.</p>
    </td></tr>"""

def email_wrap(inner):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f7f5ef;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f5ef;">
<tr><td align="center" style="padding:24px 16px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
{email_header()}
<tr><td style="padding:32px;">{inner}</td></tr>
{email_footer()}
</table></td></tr></table></body></html>"""


def admin_new_student_email(name, student_email):
    inner = f"""
    <h2 style="margin:0 0 16px;font-size:20px;color:#1a2744;">New Student Joined!</h2>
    <p style="font-size:15px;color:#2D2D2D;">A new student registered on KeepTheFlow:</p>
    <table width="100%" style="margin:16px 0;border:1px solid #e8e0c8;border-radius:8px;overflow:hidden;">
      <tr style="background:#f7f5ef;"><td style="padding:12px 16px;font-size:13px;color:#8a95a8;width:80px;">Name</td>
        <td style="padding:12px 16px;font-size:15px;color:#1a2744;font-weight:700;">{name}</td></tr>
      <tr><td style="padding:12px 16px;font-size:13px;color:#8a95a8;border-top:1px solid #e8e0c8;">Email</td>
        <td style="padding:12px 16px;font-size:15px;border-top:1px solid #e8e0c8;">
          <a href="mailto:{student_email}" style="color:#c5a44e;text-decoration:none;">{student_email}</a></td></tr>
    </table>
    <a href="{PORTAL}" style="display:inline-block;background:linear-gradient(135deg,#1a2744,#2a3a5e);color:#c5a44e;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:700;font-size:15px;">Open Portal</a>
    """
    return email_wrap(inner)


def admin_new_recordings_email(student_name, student_email, lesson_id, instances, total):
    path = LESSON_PATHS.get(lesson_id, f"lessons/{lesson_id}")
    rows = ""
    for inst in instances[:10]:
        link = f"{PORTAL}/{path}/?admin=true&scrollTo={inst}"
        rows += f'<tr><td style="padding:8px 12px;font-size:14px;color:#2D2D2D;border-bottom:1px solid #e8e0c8;">Instance #{inst}</td><td style="padding:8px 12px;text-align:right;border-bottom:1px solid #e8e0c8;"><a href="{link}" style="color:#c5a44e;font-weight:600;text-decoration:none;">Review</a></td></tr>'
    if len(instances) > 10:
        rows += f'<tr><td colspan="2" style="padding:8px 12px;font-size:13px;color:#8a95a8;">...and {len(instances)-10} more</td></tr>'

    email_line = f"<br/><span style='color:#8a95a8;font-size:13px;'>Email: {student_email}</span>" if student_email else ""
    admin_link = f"{PORTAL}/{path}/?admin=true"

    inner = f"""
    <h2 style="margin:0 0 16px;font-size:20px;color:#1a2744;">New Student Recordings</h2>
    <p style="font-size:15px;color:#2D2D2D;">
      Student <strong style="color:#1a2744;">{student_name}</strong> submitted <strong style="color:#c5a44e;">{len(instances)}</strong> new recording(s).{email_line}
    </p>
    <p style="font-size:13px;color:#8a95a8;">Total submissions: {total}</p>
    <table width="100%" style="margin:16px 0;border:1px solid #e8e0c8;border-radius:8px;overflow:hidden;">
      <tr style="background:#f7f5ef;"><th style="padding:10px 12px;text-align:left;font-size:13px;color:#8a95a8;">Instance</th><th style="padding:10px 12px;text-align:right;font-size:13px;color:#8a95a8;">Action</th></tr>
      {rows}
    </table>
    <a href="{admin_link}" style="display:inline-block;background:linear-gradient(135deg,#1a2744,#2a3a5e);color:#c5a44e;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:700;font-size:15px;">Open Admin Dashboard</a>
    """
    return email_wrap(inner)


def student_feedback_email(student_name, lesson_id, instances):
    path = LESSON_PATHS.get(lesson_id, f"lessons/{lesson_id}")
    lesson_link = f"{PORTAL}/{path}/"

    # Build a simple list of instance links
    links_html = ""
    for inst in instances[:10]:
        link = f"{PORTAL}/{path}/?scrollTo={inst}"
        links_html += f'<li><a href="{link}" style="color:#1a73e8;">Instance #{inst}</a></li>\n'

    # Simple personal-looking email (NOT a newsletter template)
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:20px;font-family:Arial,sans-serif;font-size:15px;color:#222;">
<p>Assalamu alaikum {student_name},</p>

<p>I have reviewed <b>{len(instances)}</b> of your recording{"s" if len(instances) > 1 else ""}. You can check the feedback here:</p>

<ul style="line-height:1.8;">
{links_html}</ul>

<p>Or open your lesson page directly:<br/>
<a href="{lesson_link}" style="color:#1a73e8;">{lesson_link}</a></p>

<p>Keep up the great work!</p>

<p>Best,<br/>Faris</p>
</body></html>"""
    return html


# ======= TRACKING (which notifications already sent) =======

def get_sent_keys(tag):
    """Get set of already-notified keys for a given tag."""
    rows = sb_get("qrasm_recordings", f"student_name=eq.{tag}&select=audio_url")
    return {r.get("audio_url", "") for r in rows}

def mark_sent(tag, key):
    """Mark a notification as sent."""
    try:
        sb_insert("qrasm_recordings", {
            "student_name": tag,
            "assignment_id": "keeptheflow_notifier",
            "instance_number": 0,
            "audio_url": key,
        })
    except Exception:
        pass


# ======= MAIN LOGIC =======

def run():
    print("=== KeepTheFlow Notifier v2 ===")

    # Test Supabase connection
    try:
        test = sb_get("qrasm_recordings", "select=id&limit=1")
        print(f"   Supabase OK")
    except Exception as e:
        print(f"   [FATAL] Supabase connection failed: {e}")
        sys.exit(1)

    # Get all recordings
    all_rows = sb_get("qrasm_recordings", "select=*")
    print(f"   Total rows: {len(all_rows)}")

    # Get all student emails
    try:
        all_students = sb_get("qrasm_student_emails", "select=*")
    except Exception:
        all_students = []
    print(f"   Registered students: {len(all_students)}")

    # Build email lookup
    email_lookup = {s.get("student_name", ""): s.get("email", "") for s in all_students}

    # Separate rows
    real_recordings = []
    admin_feedbacks = []
    for row in all_rows:
        sname = row.get("student_name", "")
        if sname.startswith("EMAIL_SENT_") or sname == "SYSTEM_LAST_CHECK" or sname == "ADMIN_HIDDEN":
            continue
        if sname.startswith("ADMIN_FEEDBACK_"):
            admin_feedbacks.append(row)
        elif not sname.startswith("STUDENT_EMAIL_"):
            real_recordings.append(row)

    # ---- TRIGGER 1: New student registrations ----
    sent_students = get_sent_keys("EMAIL_SENT_NEW_STUDENT")
    for s in all_students:
        sname = s.get("student_name", "")
        semail = s.get("email", "")
        if not sname or sname in sent_students:
            continue

        print(f"\n   [NEW STUDENT] {sname} ({semail})")
        html = admin_new_student_email(sname, semail)
        text = f"Assalamu alaikum,\n\nA new student has registered on Keep The Flow.\n\nName: {sname}\nEmail: {semail}\n\nYou can view the portal at {PORTAL}\n\nBest regards,\nKeep The Flow"
        if send_email(ADMIN_EMAIL, "KeepTheFlow Admin", f"{sname} joined Keep The Flow", html, text):
            mark_sent("EMAIL_SENT_NEW_STUDENT", sname)

    # ---- TRIGGER 2: New recordings -> Admin ----
    sent_subs = get_sent_keys("EMAIL_SENT_SUBMISSIONS")
    from collections import defaultdict
    groups = defaultdict(list)
    for rec in real_recordings:
        groups[(rec.get("assignment_id",""), rec.get("student_name",""))].append(rec)

    for (aid, student), recs in groups.items():
        new_instances = []
        for r in recs:
            key = f"{student}|{r.get('instance_number',0)}"
            if f"{aid}|{key}" not in sent_subs:
                new_instances.append(r.get("instance_number", 0))

        if not new_instances:
            continue

        semail = email_lookup.get(student, "")
        print(f"\n   [RECORDINGS] {student} has {len(new_instances)} new in {aid}")
        html = admin_new_recordings_email(student, semail, aid, new_instances, len(recs))
        text = f"Assalamu alaikum,\n\n{student} has submitted {len(new_instances)} new recording(s) for lesson {aid}.\n\nTotal submissions: {len(recs)}.\n\nReview them at {PORTAL}\n\nBest regards,\nKeep The Flow"
        if send_email(ADMIN_EMAIL, "KeepTheFlow Admin", f"{student} - {len(new_instances)} new recording(s)", html, text):
            for inst in new_instances:
                mark_sent("EMAIL_SENT_SUBMISSIONS", f"{aid}|{student}|{inst}")

    # ---- TRIGGER 3: Admin feedback -> Student ----
    sent_fb = get_sent_keys("EMAIL_SENT_FEEDBACK")
    fb_groups = defaultdict(list)
    for fb in admin_feedbacks:
        actual_student = fb.get("student_name", "").replace("ADMIN_FEEDBACK_", "")
        fb_groups[(fb.get("assignment_id",""), actual_student)].append(fb)

    for (aid, student), fbs in fb_groups.items():
        new_fb = []
        for fb in fbs:
            key = f"{aid}|{student}|{fb.get('instance_number',0)}"
            if key not in sent_fb:
                new_fb.append(fb.get("instance_number", 0))

        if not new_fb:
            continue

        semail = email_lookup.get(student, "")
        if not semail:
            print(f"   [SKIP] No email for {student} - cannot send feedback notification")
            for inst in new_fb:
                mark_sent("EMAIL_SENT_FEEDBACK", f"{aid}|{student}|{inst}")
            continue

        print(f"\n   [FEEDBACK] {student} has {len(new_fb)} new feedbacks in {aid}")
        html = student_feedback_email(student, aid, new_fb)
        text = f"Assalamu alaikum {student},\n\nGreat news! Your teacher has reviewed {len(new_fb)} of your recordings.\n\nVisit your lesson page to see the feedback:\n{PORTAL}/{LESSON_PATHS.get(aid, 'lessons/' + aid)}/\n\nKeep up the great work!\n\nBest regards,\nFaris"
        if send_email(semail, student, f"{student}, your recordings have been reviewed", html, text):
            for inst in new_fb:
                mark_sent("EMAIL_SENT_FEEDBACK", f"{aid}|{student}|{inst}")

    print("\n   === Done ===")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\n   [FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
