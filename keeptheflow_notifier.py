#!/usr/bin/env python3
"""
KeepTheFlow Email Notifier v3.1 (Gmail SMTP)
==============================================
Uses requests + Supabase REST API directly.
Gmail SMTP for all emails. Fancy HTML templates with deep links.

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
from collections import defaultdict
from datetime import datetime, timezone

# -- Config --
GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS", "").strip()
_gap = os.environ.get("GMAIL_APP_PASSWORD", "")
GMAIL_APP_PASSWORD = _gap.replace(" ", "") if _gap else ""
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
    url = f"{SB_URL}/rest/v1/{table}?{params}"
    r = requests.get(url, headers=SB_HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()

def sb_insert(table, data):
    url = f"{SB_URL}/rest/v1/{table}"
    r = requests.post(url, headers=SB_HEADERS, json=data, timeout=15)
    r.raise_for_status()
    return r.json()


# ======= EMAIL ENGINE (Gmail SMTP) =======

def send_email(to_email, to_name, subject, html_body, text_body):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print(f"   [SKIP] No Gmail credentials - cannot send to {to_email}")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"Keep The Flow <{GMAIL_ADDRESS}>"
    msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
    msg['Reply-To'] = GMAIL_ADDRESS
    msg['Date'] = email.utils.formatdate(localtime=False)
    domain = GMAIL_ADDRESS.split('@')[1] if '@' in GMAIL_ADDRESS else 'gmail.com'
    msg['Message-ID'] = email.utils.make_msgid(domain=domain)

    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"   [OK] Email sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"   [FATAL] Gmail Authentication Failed! Check your GMAIL_APP_PASSWORD. Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"   [FAIL] Email to {to_email}: {e}")
        return False


# ======= FANCY EMAIL TEMPLATES =======

def email_header():
    return """<tr><td style="background:linear-gradient(135deg,#1a2744,#2a3a5e);padding:28px 32px;text-align:center;">
      <h1 style="margin:0;font-size:22px;font-weight:700;color:#c5a44e;letter-spacing:0.5px;">&#10022; Keep The Flow</h1>
    </td></tr>"""

def email_footer():
    return """<tr><td style="background-color:#1a2744;padding:20px 32px;text-align:center;">
      <p style="margin:0;font-size:12px;color:#7a8a9e;">Keep The Flow &middot; Tajweed Practice Platform</p>
    </td></tr>"""

def email_wrap(inner):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f7f5ef;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f5ef;">
<tr><td align="center" style="padding:24px 16px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
{email_header()}
<tr><td style="padding:32px;">{inner}</td></tr>
{email_footer()}
</table></td></tr></table></body></html>"""


def admin_new_student_email(name, student_email):
    inner = f"""
    <h2 style="margin:0 0 16px;font-size:20px;color:#1a2744;">New Student Joined</h2>
    <p style="font-size:15px;color:#2D2D2D;line-height:1.6;">A new student registered on Keep The Flow:</p>
    <table width="100%" style="margin:16px 0;border:1px solid #e8e0c8;border-radius:8px;overflow:hidden;">
      <tr style="background:#f7f5ef;"><td style="padding:12px 16px;font-size:13px;color:#8a95a8;width:80px;">Name</td>
        <td style="padding:12px 16px;font-size:15px;color:#1a2744;font-weight:700;">{name}</td></tr>
      <tr><td style="padding:12px 16px;font-size:13px;color:#8a95a8;border-top:1px solid #e8e0c8;">Email</td>
        <td style="padding:12px 16px;font-size:15px;border-top:1px solid #e8e0c8;">
          <a href="mailto:{student_email}" style="color:#1a73e8;text-decoration:none;">{student_email}</a></td></tr>
    </table>
    <a href="{PORTAL}" style="display:inline-block;background:linear-gradient(135deg,#1a2744,#2a3a5e);color:#c5a44e;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:700;font-size:15px;">Open Portal</a>
    """
    return email_wrap(inner)


def admin_new_recordings_email(student_name, student_email, lesson_id, instances, total):
    path = LESSON_PATHS.get(lesson_id, f"lessons/{lesson_id}")
    rows = ""
    for inst in instances[:10]:
        link = f"{PORTAL}/{path}/?admin=true&scrollTo={inst}"
        rows += f'<tr><td style="padding:8px 12px;font-size:14px;color:#2D2D2D;border-bottom:1px solid #e8e0c8;">Instance #{inst}</td><td style="padding:8px 12px;text-align:right;border-bottom:1px solid #e8e0c8;"><a href="{link}" style="color:#1a73e8;font-weight:600;text-decoration:none;">Review</a></td></tr>'
    if len(instances) > 10:
        rows += f'<tr><td colspan="2" style="padding:8px 12px;font-size:13px;color:#8a95a8;">...and {len(instances)-10} more</td></tr>'

    email_line = f"<br/><span style='color:#8a95a8;font-size:13px;'>Email: {student_email}</span>" if student_email else ""
    admin_link = f"{PORTAL}/{path}/?admin=true"

    inner = f"""
    <h2 style="margin:0 0 16px;font-size:20px;color:#1a2744;">New Student Recordings</h2>
    <p style="font-size:15px;color:#2D2D2D;line-height:1.6;">
      <strong style="color:#1a2744;">{student_name}</strong> submitted <strong style="color:#c5a44e;">{len(instances)}</strong> new recording(s).{email_line}
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
    rows = ""
    for inst in instances[:10]:
        link = f"{PORTAL}/{path}/?scrollTo={inst}"
        rows += f'<tr><td style="padding:8px 12px;font-size:14px;color:#2D2D2D;border-bottom:1px solid #e8e0c8;">Instance #{inst}</td><td style="padding:8px 12px;text-align:right;border-bottom:1px solid #e8e0c8;"><a href="{link}" style="color:#1a73e8;font-weight:600;text-decoration:none;">Check Feedback</a></td></tr>'

    inner = f"""
    <h2 style="margin:0 0 16px;font-size:20px;color:#1a2744;">Your Recordings Have Been Reviewed</h2>
    <p style="font-size:15px;color:#2D2D2D;line-height:1.6;">Assalamu alaikum {student_name},</p>
    <p style="font-size:15px;color:#2D2D2D;line-height:1.6;">Your teacher has reviewed <strong style="color:#c5a44e;">{len(instances)}</strong> of your recordings. Click below to see your feedback:</p>
    <table width="100%" style="margin:16px 0;border:1px solid #e8e0c8;border-radius:8px;overflow:hidden;">
      <tr style="background:#f7f5ef;"><th style="padding:10px 12px;text-align:left;font-size:13px;color:#8a95a8;">Instance</th><th style="padding:10px 12px;text-align:right;font-size:13px;color:#8a95a8;">Action</th></tr>
      {rows}
    </table>
    <a href="{PORTAL}/{path}/" style="display:inline-block;background:linear-gradient(135deg,#1a2744,#2a3a5e);color:#c5a44e;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:700;font-size:15px;">Open Your Lesson</a>
    <hr style="border:none;border-top:1px solid #e8e0c8;margin:24px 0;"/>
    <p style="font-size:15px;color:#2D2D2D;line-height:1.6;">Keep up the great work!<br/>Best,<br/>Your Teacher</p>
    """
    return email_wrap(inner)


# ======= TRACKING =======

def get_sent_keys(tag):
    rows = sb_get("qrasm_recordings", f"student_name=eq.{tag}&select=audio_url")
    return {r.get("audio_url", "") for r in rows}

def mark_sent(tag, key):
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
    print("=== KeepTheFlow Notifier v3.2 ===")
    print(f"   Gmail address: {GMAIL_ADDRESS or 'NOT SET'}")
    print(f"   Gmail password: {'SET (' + str(len(GMAIL_APP_PASSWORD)) + ' chars)' if GMAIL_APP_PASSWORD else 'NOT SET'}")

    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("   [FATAL] Gmail credentials missing! Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD.")
        sys.exit(1)

    try:
        test = sb_get("qrasm_recordings", "select=id&limit=1")
        print(f"   Supabase: OK")
    except Exception as e:
        print(f"   [FATAL] Supabase connection failed: {e}")
        sys.exit(1)

    all_rows = sb_get("qrasm_recordings", "select=*")
    print(f"   Total rows: {len(all_rows)}")

    try:
        all_students = sb_get("qrasm_student_emails", "select=*")
    except Exception:
        all_students = []
    print(f"   Registered students: {len(all_students)}")

    email_lookup = {s.get("student_name", ""): s.get("email", "") for s in all_students}

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

    # ---- TRIGGER 1: New students ----
    sent_students = get_sent_keys("EMAIL_SENT_NEW_STUDENT")
    for s in all_students:
        sname = s.get("student_name", "")
        semail = s.get("email", "")
        if not sname or sname in sent_students:
            continue
        print(f"\n   [NEW STUDENT] {sname} ({semail})")
        html = admin_new_student_email(sname, semail)
        text = f"New student registered: {sname} ({semail}). View portal at {PORTAL}"
        if send_email(ADMIN_EMAIL, "Admin", f"{sname} joined Keep The Flow", html, text):
            mark_sent("EMAIL_SENT_NEW_STUDENT", sname)

    # ---- TRIGGER 2: New recordings ----
    sent_subs = get_sent_keys("EMAIL_SENT_SUBMISSIONS")
    groups = defaultdict(list)
    for rec in real_recordings:
        groups[(rec.get("assignment_id",""), rec.get("student_name",""))].append(rec)

    for (aid, student), recs in groups.items():
        new_instances = []
        for r in recs:
            key = f"{aid}|{student}|{r.get('instance_number',0)}"
            if key not in sent_subs:
                new_instances.append(r.get("instance_number", 0))
        if not new_instances:
            continue
        semail = email_lookup.get(student, "")
        print(f"\n   [RECORDINGS] {student} has {len(new_instances)} new in {aid}")
        html = admin_new_recordings_email(student, semail, aid, new_instances, len(recs))
        text = f"{student} submitted {len(new_instances)} recording(s) for {aid}. Review at {PORTAL}"
        if send_email(ADMIN_EMAIL, "Admin", f"{student} - {len(new_instances)} new recording(s)", html, text):
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
            print(f"   [SKIP] No email for {student}")
            for inst in new_fb:
                mark_sent("EMAIL_SENT_FEEDBACK", f"{aid}|{student}|{inst}")
            continue

        print(f"\n   [FEEDBACK] {student} has {len(new_fb)} new feedbacks in {aid}")
        html = student_feedback_email(student, aid, new_fb)
        text = f"Assalamu alaikum {student},\n\nYour teacher has reviewed {len(new_fb)} of your recordings.\n\nVisit: {PORTAL}/{LESSON_PATHS.get(aid, 'lessons/' + aid)}/\n\nBest,\nYour Teacher"
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
