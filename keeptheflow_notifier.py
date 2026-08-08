#!/usr/bin/env python3
"""
KeepTheFlow Automated Email Notifier
=====================================
Runs alongside wa_reminder.py via GitHub Actions (every 30 minutes).

Flow:
  1. New student registers → Admin gets notified with name + email
  2. Student records instances → Admin gets notified with deep links
  3. Admin gives feedback → Student gets notified with deep links

Uses the same Gmail SMTP + anti-spam logic as the notionA Tri-Literal system.
"""

import os
import sys
import json
import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

try:
    from supabase import create_client, Client
except ImportError:
    print("⚠ supabase package not installed, skipping KeepTheFlow notifier")
    sys.exit(0)

# ── Configuration (reuses existing wa_reminder.py GitHub secrets) ─────
GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
ADMIN_EMAIL        = "lightknightf1@gmail.com"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lhebavvnrwqojbhyodwc.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_JW75ayCf5SbvyT-02GmjNQ_vFpivPTU")

# ── Portal base URL (Vercel deployment) ──
PORTAL_BASE = "https://keep-the-flow.vercel.app"

# ── Lesson ID → URL path mapping ──
LESSON_PATHS = {
    "idgham_yw_lesson": "lessons/idgham-yw-5-12",
}

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ═══════════════════════════════════════════════════════════════════════
# EMAIL ENGINE (mirrors wa_reminder.py anti-spam headers exactly)
# ═══════════════════════════════════════════════════════════════════════

def get_admin_notification_html(student_name, student_email, lesson_id, instances, total_count):
    """Generate the HTML email sent to the admin when a student submits new recordings."""
    lesson_path = LESSON_PATHS.get(lesson_id, f"lessons/{lesson_id}")

    # Build instance links
    instance_links = ""
    for inst in instances[:10]:  # Cap at 10 links to keep email clean
        link = f"{PORTAL_BASE}/{lesson_path}/?admin=true&scrollTo={inst}"
        instance_links += f'<tr><td style="padding:8px 12px;font-size:14px;color:#2D2D2D;border-bottom:1px solid #e8e0c8;">Instance #{inst}</td><td style="padding:8px 12px;text-align:right;border-bottom:1px solid #e8e0c8;"><a href="{link}" style="color:#c5a44e;font-weight:600;text-decoration:none;">Review →</a></td></tr>'

    if len(instances) > 10:
        instance_links += f'<tr><td colspan="2" style="padding:8px 12px;font-size:13px;color:#8a95a8;">...and {len(instances)-10} more</td></tr>'

    admin_link = f"{PORTAL_BASE}/{lesson_path}/?admin=true"
    email_info = f"<br/><span style='color:#8a95a8;font-size:13px;'>Email: {student_email}</span>" if student_email else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>New Student Recordings</title></head>
<body style="margin:0;padding:0;background-color:#f7f5ef;font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f5ef;">
    <tr><td align="center" style="padding:24px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <tr><td style="background:linear-gradient(135deg,#1a2744 0%,#2a3a5e 100%);padding:28px 32px;text-align:center;">
          <h1 style="margin:0;font-size:22px;font-weight:700;color:#c5a44e;letter-spacing:0.5px;">✦ LightKnight Flow</h1>
        </td></tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 16px;font-size:20px;color:#1a2744;font-weight:600;">🎙️ New Student Recordings</h2>
          <p style="margin:0 0 14px;font-size:15px;color:#2D2D2D;line-height:1.6;">
            Student <strong style="color:#1a2744;">{student_name}</strong> has submitted <strong style="color:#c5a44e;">{len(instances)}</strong> new recording(s).{email_info}
          </p>
          <p style="margin:0 0 8px;font-size:13px;color:#8a95a8;">Total submissions for this lesson: {total_count}</p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;border:1px solid #e8e0c8;border-radius:8px;overflow:hidden;">
            <tr style="background:#f7f5ef;"><th style="padding:10px 12px;text-align:left;font-size:13px;color:#8a95a8;font-weight:600;">Instance</th><th style="padding:10px 12px;text-align:right;font-size:13px;color:#8a95a8;font-weight:600;">Action</th></tr>
            {instance_links}
          </table>
          <a href="{admin_link}" style="display:inline-block;background:linear-gradient(135deg,#1a2744,#2a3a5e);color:#c5a44e;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:700;font-size:15px;margin-top:8px;">Open Admin Dashboard →</a>
          <hr style="border:none;border-top:1px solid #e8e0c8;margin:24px 0;"/>
          <p style="margin:0;font-size:15px;color:#2D2D2D;line-height:1.6;">Best,<br/>The LightKnight System</p>
        </td></tr>
        <tr><td style="background-color:#1a2744;padding:24px 32px;text-align:center;">
          <p style="margin:0;font-size:13px;color:#a0aec0;">Automated notification from KeepTheFlow.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def get_student_notification_html(student_name, lesson_id, instances):
    """Generate the HTML email sent to the student when the admin gives feedback."""
    lesson_path = LESSON_PATHS.get(lesson_id, f"lessons/{lesson_id}")

    instance_links = ""
    for inst in instances[:10]:
        link = f"{PORTAL_BASE}/{lesson_path}/?scrollTo={inst}"
        instance_links += f'<tr><td style="padding:8px 12px;font-size:14px;color:#2D2D2D;border-bottom:1px solid #e8e0c8;">Instance #{inst}</td><td style="padding:8px 12px;text-align:right;border-bottom:1px solid #e8e0c8;"><a href="{link}" style="color:#c5a44e;font-weight:600;text-decoration:none;">Check Feedback →</a></td></tr>'

    if len(instances) > 10:
        instance_links += f'<tr><td colspan="2" style="padding:8px 12px;font-size:13px;color:#8a95a8;">...and {len(instances)-10} more</td></tr>'

    lesson_link = f"{PORTAL_BASE}/{lesson_path}/"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>Your Homework Has Been Reviewed!</title></head>
<body style="margin:0;padding:0;background-color:#f7f5ef;font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f5ef;">
    <tr><td align="center" style="padding:24px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <tr><td style="background:linear-gradient(135deg,#1a2744 0%,#2a3a5e 100%);padding:28px 32px;text-align:center;">
          <h1 style="margin:0;font-size:22px;font-weight:700;color:#c5a44e;letter-spacing:0.5px;">✦ LightKnight Flow</h1>
        </td></tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 16px;font-size:20px;color:#1a2744;font-weight:600;">🎓 Your Homework Has Been Reviewed!</h2>
          <p style="margin:0 0 14px;font-size:15px;color:#2D2D2D;line-height:1.6;">
            سلامٌ عليكم <strong style="color:#1a2744;">{student_name}</strong>,
          </p>
          <p style="margin:0 0 14px;font-size:15px;color:#2D2D2D;line-height:1.6;">
            Great news! Your teacher has reviewed <strong style="color:#c5a44e;">{len(instances)}</strong> of your recordings. Click below to see your feedback:
          </p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;border:1px solid #e8e0c8;border-radius:8px;overflow:hidden;">
            <tr style="background:#f7f5ef;"><th style="padding:10px 12px;text-align:left;font-size:13px;color:#8a95a8;font-weight:600;">Instance</th><th style="padding:10px 12px;text-align:right;font-size:13px;color:#8a95a8;font-weight:600;">Action</th></tr>
            {instance_links}
          </table>
          <a href="{lesson_link}" style="display:inline-block;background:linear-gradient(135deg,#1a2744,#2a3a5e);color:#c5a44e;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:700;font-size:15px;margin-top:8px;">Open Your Lesson →</a>
          <hr style="border:none;border-top:1px solid #e8e0c8;margin:24px 0;"/>
          <p style="margin:0;font-size:15px;color:#2D2D2D;line-height:1.6;">Keep up the great work!<br/>Best,<br/>Faris</p>
        </td></tr>
        <tr><td style="background-color:#1a2744;padding:24px 32px;text-align:center;">
          <p style="margin:0;font-size:13px;color:#a0aec0;">Automated notification from KeepTheFlow.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def get_new_student_html(student_name, student_email):
    """Generate the HTML email sent to admin when a new student registers."""
    portal_link = f"{PORTAL_BASE}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>New Student Joined</title></head>
<body style="margin:0;padding:0;background-color:#f7f5ef;font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f5ef;">
    <tr><td align="center" style="padding:24px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <tr><td style="background:linear-gradient(135deg,#1a2744 0%,#2a3a5e 100%);padding:28px 32px;text-align:center;">
          <h1 style="margin:0;font-size:22px;font-weight:700;color:#c5a44e;letter-spacing:0.5px;">✦ LightKnight Flow</h1>
        </td></tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 16px;font-size:20px;color:#1a2744;font-weight:600;">🆕 New Student Joined!</h2>
          <p style="margin:0 0 14px;font-size:15px;color:#2D2D2D;line-height:1.6;">Hello Admin,</p>
          <p style="margin:0 0 14px;font-size:15px;color:#2D2D2D;line-height:1.6;">A new student has registered on the KeepTheFlow platform:</p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;border:1px solid #e8e0c8;border-radius:8px;overflow:hidden;">
            <tr style="background:#f7f5ef;"><td style="padding:12px 16px;font-size:13px;color:#8a95a8;font-weight:600;width:100px;">Name</td><td style="padding:12px 16px;font-size:15px;color:#1a2744;font-weight:700;">{student_name}</td></tr>
            <tr><td style="padding:12px 16px;font-size:13px;color:#8a95a8;font-weight:600;border-top:1px solid #e8e0c8;">Email</td><td style="padding:12px 16px;font-size:15px;color:#1a2744;border-top:1px solid #e8e0c8;"><a href="mailto:{student_email}" style="color:#c5a44e;text-decoration:none;">{student_email}</a></td></tr>
          </table>
          <a href="{portal_link}" style="display:inline-block;background:linear-gradient(135deg,#1a2744,#2a3a5e);color:#c5a44e;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:700;font-size:15px;margin-top:8px;">Open Portal →</a>
          <hr style="border:none;border-top:1px solid #e8e0c8;margin:24px 0;"/>
          <p style="margin:0;font-size:15px;color:#2D2D2D;line-height:1.6;">Best,<br/>The LightKnight System</p>
        </td></tr>
        <tr><td style="background-color:#1a2744;padding:24px 32px;text-align:center;">
          <p style="margin:0;font-size:13px;color:#a0aec0;">Automated notification from KeepTheFlow.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def send_email(to_email, to_name, subject, html_content, text_fallback):
    """Send email using the exact same SMTP + anti-spam approach as wa_reminder.py."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("   ⚠ Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD — skipping email")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"LightKnight Flow <{GMAIL_ADDRESS}>"
    msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
    msg['Reply-To'] = GMAIL_ADDRESS
    msg['Date'] = email.utils.formatdate(localtime=False)

    # Domain alignment to prevent Yahoo/iCloud spam flags (from notionA)
    domain = GMAIL_ADDRESS.split('@')[1] if '@' in GMAIL_ADDRESS else 'gmail.com'
    msg['Message-ID'] = email.utils.make_msgid(domain=domain)

    # Plain text first, HTML last (per RFC — HTML must be attached LAST)
    msg.attach(MIMEText(text_fallback, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"   ✓ Sent email to {to_email} ({subject})")
        return True
    except Exception as e:
        print(f"   ✗ Failed to send to {to_email}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════
# CORE LOGIC
# ═══════════════════════════════════════════════════════════════════════

def get_last_check_timestamp():
    """Read the last-check timestamp from Supabase state tracking."""
    try:
        res = sb.table("qrasm_recordings").select("audio_url") \
            .eq("student_name", "SYSTEM_LAST_CHECK") \
            .eq("assignment_id", "keeptheflow_notifier") \
            .limit(1).execute()
        if res.data and res.data[0].get("audio_url"):
            return res.data[0]["audio_url"]
    except:
        pass
    return None


def set_last_check_timestamp(ts_str):
    """Update the last-check timestamp in Supabase."""
    try:
        # Delete old
        sb.table("qrasm_recordings").delete() \
            .eq("student_name", "SYSTEM_LAST_CHECK") \
            .eq("assignment_id", "keeptheflow_notifier").execute()
        # Insert new
        sb.table("qrasm_recordings").insert({
            "student_name": "SYSTEM_LAST_CHECK",
            "assignment_id": "keeptheflow_notifier",
            "instance_number": 0,
            "audio_url": ts_str
        }).execute()
    except Exception as e:
        print(f"   ⚠ Failed to save check timestamp: {e}")


def get_student_email(student_name):
    """Look up a student's email from the qrasm_student_emails table."""
    try:
        res = sb.table("qrasm_student_emails").select("email") \
            .eq("student_name", student_name).limit(1).execute()
        if res.data:
            return res.data[0].get("email", "")
    except:
        pass
    return ""


def run():
    print("═══ KeepTheFlow Notifier ═══")
    now_str = datetime.now(timezone.utc).isoformat()
    last_check = get_last_check_timestamp()

    print(f"   Last check: {last_check or 'NEVER (first run)'}")
    print(f"   Current:    {now_str}")

    # ── Fetch ALL recordings ──
    try:
        res = sb.table("qrasm_recordings").select("*").execute()
        all_rows = res.data or []
    except Exception as e:
        print(f"   ✗ Failed to fetch recordings: {e}")
        return

    # Filter out system/tracking rows
    real_recordings = []     # Student submissions
    admin_feedbacks = []     # ADMIN_FEEDBACK_* rows
    notified_submissions = set()  # (assignment_id, student_name, instance_number) already notified
    notified_feedbacks = set()

    for row in all_rows:
        sname = row.get("student_name", "")
        aid = row.get("assignment_id", "")
        inst = row.get("instance_number", 0)
        created = row.get("created_at", "")

        # Skip system rows
        if sname in ("SYSTEM_LAST_CHECK", "ADMIN_HIDDEN", "EMAIL_SENT_SUBMISSIONS", "EMAIL_SENT_FEEDBACK"):
            # Track previously notified items
            if sname == "EMAIL_SENT_SUBMISSIONS":
                target = row.get("audio_url", "")  # "student_name|instance_number"
                notified_submissions.add(f"{aid}|{target}")
            elif sname == "EMAIL_SENT_FEEDBACK":
                target = row.get("audio_url", "")
                notified_feedbacks.add(f"{aid}|{target}")
            continue

        if sname.startswith("ADMIN_FEEDBACK_"):
            actual_student = sname.replace("ADMIN_FEEDBACK_", "")
            admin_feedbacks.append({
                "assignment_id": aid,
                "student_name": actual_student,
                "instance_number": inst,
                "created_at": created,
                "key": f"{aid}|{actual_student}|{inst}"
            })
        elif not sname.startswith("STUDENT_EMAIL_"):
            real_recordings.append({
                "assignment_id": aid,
                "student_name": sname,
                "instance_number": inst,
                "created_at": created,
                "key": f"{aid}|{sname}|{inst}"
            })

    # ══════════════════════════════════════════════════════════════════
    # 1. ADMIN NOTIFICATIONS: New student submissions
    # ══════════════════════════════════════════════════════════════════
    # Group recordings by (assignment_id, student_name)
    from collections import defaultdict
    student_groups = defaultdict(list)
    for rec in real_recordings:
        student_groups[(rec["assignment_id"], rec["student_name"])].append(rec)

    for (aid, student), recs in student_groups.items():
        # Find NEW recordings (not yet notified)
        new_instances = []
        for r in recs:
            notify_key = f"{aid}|{student}|{r['instance_number']}"
            if notify_key not in notified_submissions:
                new_instances.append(r["instance_number"])

        if not new_instances:
            continue

        total_count = len(recs)
        student_email = get_student_email(student)

        print(f"\n   📬 Admin Notify: {student} has {len(new_instances)} new recordings in {aid}")

        # Build admin email
        subject = f"📝 {student} submitted {len(new_instances)} new recording(s)"
        html = get_admin_notification_html(student, student_email, aid, new_instances, total_count)
        text = f"{student} submitted {len(new_instances)} new recordings in {aid}. Total: {total_count}."

        if send_email(ADMIN_EMAIL, "LightKnight Admin", subject, html, text):
            # Mark all as notified
            for inst in new_instances:
                try:
                    sb.table("qrasm_recordings").insert({
                        "student_name": "EMAIL_SENT_SUBMISSIONS",
                        "assignment_id": aid,
                        "instance_number": 0,
                        "audio_url": f"{student}|{inst}"
                    }).execute()
                except:
                    pass

    # ══════════════════════════════════════════════════════════════════
    # 2. STUDENT NOTIFICATIONS: New admin feedback
    # ══════════════════════════════════════════════════════════════════
    feedback_groups = defaultdict(list)
    for fb in admin_feedbacks:
        feedback_groups[(fb["assignment_id"], fb["student_name"])].append(fb)

    for (aid, student), fbs in feedback_groups.items():
        # Find NEW feedbacks
        new_fb_instances = []
        for fb in fbs:
            notify_key = f"{aid}|{student}|{fb['instance_number']}"
            if notify_key not in notified_feedbacks:
                new_fb_instances.append(fb["instance_number"])

        if not new_fb_instances:
            continue

        student_email = get_student_email(student)
        if not student_email:
            print(f"   ⚠ No email for {student} — cannot notify about feedback")
            # Still mark as processed to avoid repeat logs
            for inst in new_fb_instances:
                try:
                    sb.table("qrasm_recordings").insert({
                        "student_name": "EMAIL_SENT_FEEDBACK",
                        "assignment_id": aid,
                        "instance_number": 0,
                        "audio_url": f"{student}|{inst}"
                    }).execute()
                except:
                    pass
            continue

        print(f"\n   📬 Student Notify: {student} ({student_email}) has {len(new_fb_instances)} new feedbacks in {aid}")

        subject = f"🎓 Your homework has been reviewed!"
        html = get_student_notification_html(student, aid, new_fb_instances)
        text = f"سلامٌ عليكم {student}, your teacher has reviewed {len(new_fb_instances)} of your recordings. Check your lesson page for feedback."

        if send_email(student_email, student, subject, html, text):
            for inst in new_fb_instances:
                try:
                    sb.table("qrasm_recordings").insert({
                        "student_name": "EMAIL_SENT_FEEDBACK",
                        "assignment_id": aid,
                        "instance_number": 0,
                        "audio_url": f"{student}|{inst}"
                    }).execute()
                except:
                    pass

    # ══════════════════════════════════════════════════════════════════
    # 3. NEW STUDENT REGISTRATION: Notify admin
    # ══════════════════════════════════════════════════════════════════
    try:
        students_res = sb.table("qrasm_student_emails").select("*").execute()
        all_students = students_res.data or []
    except Exception as e:
        print(f"   ⚠ Failed to fetch student emails: {e}")
        all_students = []

    # Find which students we already notified about
    notified_students = set()
    for row in all_rows:
        if row.get("student_name") == "EMAIL_SENT_NEW_STUDENT":
            notified_students.add(row.get("audio_url", ""))

    for student_row in all_students:
        sname = student_row.get("student_name", "")
        semail = student_row.get("email", "")
        if not sname or sname in notified_students:
            continue

        print(f"\n   🆕 New Student: {sname} ({semail})")

        subject = f"🆕 New student joined: {sname}"
        html = get_new_student_html(sname, semail)
        text = f"New student joined KeepTheFlow.\nName: {sname}\nEmail: {semail}"

        if send_email(ADMIN_EMAIL, "LightKnight Admin", subject, html, text):
            try:
                sb.table("qrasm_recordings").insert({
                    "student_name": "EMAIL_SENT_NEW_STUDENT",
                    "assignment_id": "keeptheflow_notifier",
                    "instance_number": 0,
                    "audio_url": sname
                }).execute()
            except:
                pass

    # Save checkpoint
    set_last_check_timestamp(now_str)
    print(f"\n   ✓ Check complete at {now_str}")


if __name__ == "__main__":
    run()
