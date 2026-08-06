#!/usr/bin/env python3
import os
import sys
import json
import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
try:
    from supabase import create_client, Client
except ImportError:
    print("pip install supabase")
    sys.exit(1)

# Configuration (Uses existing wa_reminder.py secrets)
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
ADMIN_EMAIL = "lightknightf1@gmail.com"

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lhebavvnrwqojbhyodwc.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_JW75ayCf5SbvyT-02GmjNQ_vFpivPTU")
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_html_email(title, greeting, message_lines, is_admin=False):
    lines_html = "".join([f'<p style="margin:0 0 14px;font-size:15px;color:#2D2D2D;line-height:1.6;">{line}</p>' for line in message_lines])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>KeepTheFlow Notification</title>
</head>
<body style="margin:0;padding:0;background-color:#f7f5ef;font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f5ef;">
    <tr>
      <td align="center" style="padding:24px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
          <tr>
            <td style="background:linear-gradient(135deg,#1a2744 0%,#2a3a5e 100%);padding:28px 32px;text-align:center;">
              <h1 style="margin:0;font-size:22px;font-weight:700;color:#c5a44e;letter-spacing:0.5px;">
                ✦ LightKnight Flow
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              <h2 style="margin:0 0 16px;font-size:20px;color:#1a2744;font-weight:600;">{title}</h2>
              <p style="margin:0 0 14px;font-size:15px;color:#2D2D2D;line-height:1.6;">{greeting},</p>
              {lines_html}
              <hr style="border:none;border-top:1px solid #e8e0c8;margin:20px 0;" />
              <p style="margin:0;font-size:15px;color:#2D2D2D;line-height:1.6;">Best,<br/>The LightKnight System</p>
            </td>
          </tr>
          <tr>
            <td style="background-color:#1a2744;padding:24px 32px;text-align:center;">
              <p style="margin:0;font-size:13px;color:#a0aec0;">This is an automated notification from KeepTheFlow.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

def send_email(to_email, to_name, subject, html_content, text_fallback):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD. Cannot send email.")
        return False
        
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"LightKnight Flow <{GMAIL_ADDRESS}>"
    msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
    msg['Reply-To'] = GMAIL_ADDRESS
    msg['Date'] = email.utils.formatdate(localtime=False)
    
    domain = GMAIL_ADDRESS.split('@')[1] if '@' in GMAIL_ADDRESS else 'gmail.com'
    msg['Message-ID'] = email.utils.make_msgid(domain=domain)
    
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

def run():
    print("Fetching recordings from Supabase...")
    res = sb.table("qrasm_recordings").select("*").execute()
    data = res.data
    
    # Track states
    # submission_state[assignment_id][student_name] = max_threshold_sent
    # feedback_state[assignment_id][student_name] = max_threshold_sent
    submission_state = defaultdict(lambda: defaultdict(int))
    feedback_state = defaultdict(lambda: defaultdict(int))
    
    # Counts
    student_submissions = defaultdict(lambda: defaultdict(int))
    admin_feedbacks = defaultdict(lambda: defaultdict(int))
    
    # Process data
    for row in data:
        sname = row.get("student_name", "")
        aid = row.get("assignment_id", "")
        
        # State tracking rows
        if sname == "EMAIL_SENT_SUBMISSIONS":
            target_student = row.get("audio_url", "")
            thresh = row.get("instance_number", 0)
            if thresh > submission_state[aid][target_student]:
                submission_state[aid][target_student] = thresh
            continue
            
        if sname == "EMAIL_SENT_FEEDBACK":
            target_student = row.get("audio_url", "")
            thresh = row.get("instance_number", 0)
            if thresh > feedback_state[aid][target_student]:
                feedback_state[aid][target_student] = thresh
            continue
            
        # Actual records
        if sname.startswith("ADMIN_FEEDBACK_"):
            actual_student = sname.replace("ADMIN_FEEDBACK_", "")
            admin_feedbacks[aid][actual_student] += 1
        else:
            student_submissions[aid][sname] += 1

    # 1. Check Submissions (Notify Admin)
    for aid, students in student_submissions.items():
        for student, count in students.items():
            threshold = (count // 5) * 5
            if threshold >= 5 and threshold > submission_state[aid][student]:
                print(f"Trigger: Admin Notify -> {student} reached {threshold} submissions in {aid}")
                
                subject = f"Student Milestone: {student} reached {threshold} submissions"
                greeting = "Hello Admin"
                lines = [
                    f"Great news! Your student <strong>{student}</strong> has just submitted their <strong>{threshold}th</strong> recording for the lesson <em>{aid}</em>.",
                    "Please log into the portal to review their progress and provide feedback."
                ]
                text_fb = f"{greeting},\n\nStudent {student} reached {threshold} submissions in {aid}.\n\nBest,\nLightKnight System"
                html = get_html_email(subject, greeting, lines, is_admin=True)
                
                if send_email(ADMIN_EMAIL, "LightKnight Admin", subject, html, text_fb):
                    # Save state
                    sb.table("qrasm_recordings").insert({
                        "student_name": "EMAIL_SENT_SUBMISSIONS",
                        "assignment_id": aid,
                        "instance_number": threshold,
                        "audio_url": student
                    }).execute()
                    
    # 2. Check Feedback (Notify Student)
    # We don't have the student's email natively in Supabase (it's in localStorage).
    # But if they don't provide it, we can't email them. 
    # For now, we will log it. In the future, if you add email to the DB, we can pull it here.
    for aid, students in admin_feedbacks.items():
        for student, count in students.items():
            threshold = (count // 5) * 5
            if threshold >= 5 and threshold > feedback_state[aid][student]:
                print(f"Trigger: Student Notify -> Admin reached {threshold} feedbacks for {student} in {aid}")
                # Without the student's email in the DB, we can't send it directly from this backend script.
                # To fix this, we'll need the frontend to send the email to Supabase when they log in.
                # For now, we mark it as processed so it doesn't loop.
                sb.table("qrasm_recordings").insert({
                    "student_name": "EMAIL_SENT_FEEDBACK",
                    "assignment_id": aid,
                    "instance_number": threshold,
                    "audio_url": student
                }).execute()

if __name__ == "__main__":
    run()
