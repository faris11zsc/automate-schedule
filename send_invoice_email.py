import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email.utils

def run():
    GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "").strip()
    _gap2 = os.environ.get("GMAIL_APP_PASSWORD", "")
    GMAIL_APP_PASSWORD = _gap2.replace(" ", "") if _gap2 else ""
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>LightKnight Academy - August 2026 Final</title>
  <style>
    body { margin: 0; padding: 20px; background-color: #f7f5ef; font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #2D2D2D; }
    .invoice-container { max-width: 800px; margin: 0 auto; background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }
    .header { background-color: #1a2744; padding: 40px 20px; text-align: center; }
    .header h1 { margin: 0; font-size: 32px; color: #c5a44e; font-weight: 700; }
    .header p { margin: 8px 0 0; color: #a0aec0; font-size: 16px; }
    .content { padding: 40px; }
    .invoice-title { font-size: 24px; font-weight: bold; color: #1a2744; margin-top: 0; margin-bottom: 20px; }
    .info-box { background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 40px; border-left: 4px solid #1a2744; }
    .info-box p { margin: 5px 0; font-size: 16px; }
    .section-title { font-size: 20px; color: #1a2744; margin-bottom: 15px; padding-bottom: 5px; border-bottom: 2px solid #c5a44e; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 40px; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
    th { background-color: #f7f5ef; color: #1a2744; font-weight: 600; }
    .subtotal-row td { background-color: #f7f5ef; font-weight: bold; color: #1a2744; border-bottom: none; }
    .total-box { background-color: #1a2744; color: white; padding: 30px; border-radius: 8px; text-align: right; margin-bottom: 30px; }
    .total-box span { display: block; }
    .total-title { font-size: 16px; color: #cbd5e0; margin-bottom: 5px; }
    .total-value { font-size: 32px; color: #c5a44e; font-weight: bold; }
    .paypal-container { text-align: center; margin-bottom: 40px; }
    .paypal-btn { display: inline-block; background-color: #c5a44e; color: #1a2744; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-weight: bold; font-size: 18px; transition: background-color 0.2s; }
    .paypal-btn:hover { background-color: #b08d3c; }
    .footer { text-align: center; padding-bottom: 40px; color: #718096; font-size: 14px; background-color: #f7f5ef; }
  </style>
</head>
<body>
  <div class="invoice-container">
    <div class="header">
      <h1>LightKnight Academy</h1>
      <p>Premium Online Qur'an & Islamic Studies</p>
    </div>
    
    <div class="content">
      <h2 class="invoice-title">Report for August 2026</h2>
      <div class="info-box">
        <p><strong>Students:</strong> Youssef & Omar</p>
        <p><strong>Billing Period:</strong> August 1, 2026 - August 31, 2026</p>
      </div>

      <h3 class="section-title">Youssef's Attendance (Sat & Tue &rarr; Tue & Thu)</h3>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>August 1, 2026 (Saturday)</td><td>Attended</td></tr>
          <tr><td>August 4, 2026 (Tuesday)</td><td>Attended</td></tr>
          <tr><td>August 8, 2026 (Saturday)</td><td>Attended</td></tr>
          <tr><td>August 11, 2026 (Tuesday)</td><td>Rescheduled</td></tr>
          <tr><td>August 13, 2026 (Thursday)</td><td>Attended</td></tr>
          <tr><td>August 15, 2026 (Saturday)</td><td>Canceled</td></tr>
          <tr><td>August 18, 2026 (Tuesday)</td><td>Canceled</td></tr>
          <tr><td>August 20, 2026 (Thursday)</td><td>Attended</td></tr>
          <tr><td>August 25, 2026 (Tuesday)</td><td>Attended</td></tr>
          <tr><td>August 27, 2026 (Thursday)</td><td>Attended</td></tr>
        </tbody>
        <tfoot>
          <tr class="subtotal-row">
            <td colspan="2">Youssef Subtotal: 7 sessions attended</td>
          </tr>
        </tfoot>
      </table>

      <h3 class="section-title">Omar's Attendance (Sun & Wed)</h3>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>August 2, 2026 (Sunday)</td><td>Attended</td></tr>
          <tr><td>August 5, 2026 (Wednesday)</td><td>Attended</td></tr>
          <tr><td>August 9, 2026 (Sunday)</td><td>Attended</td></tr>
          <tr><td>August 12, 2026 (Wednesday)</td><td>Attended</td></tr>
          <tr><td>August 16, 2026 (Sunday)</td><td>Canceled</td></tr>
          <tr><td>August 19, 2026 (Wednesday)</td><td>Attended</td></tr>
          <tr><td>August 23, 2026 (Sunday)</td><td>Attended</td></tr>
          <tr><td>August 26, 2026 (Wednesday)</td><td>Canceled</td></tr>
          <tr><td>August 30, 2026 (Sunday)</td><td>Attended</td></tr>
        </tbody>
        <tfoot>
          <tr class="subtotal-row">
            <td colspan="2">Omar Subtotal: 7 sessions attended</td>
          </tr>
        </tfoot>
      </table>

      <div class="total-box">
        <span class="total-title">Total Sessions Attended</span>
        <span class="total-value">14 Sessions</span>
      </div>

      <div class="paypal-container">
        <a href="https://paypal.me/FarisOransa58/" target="_blank" class="paypal-btn">Pay Invoice via PayPal</a>
      </div>
    </div>
    
    <div class="footer">
      <p><br>Thank you for choosing <strong>LightKnight Academy</strong>.<br>If you have any questions about this report, please reply to this email.</p>
    </div>
  </div>
</body>
</html>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'LightKnight Academy Report - August 2026 (Omar & Youssef)'
    msg['From'] = f"Faris Oransa <{GMAIL_ADDRESS}>"
    msg['To'] = f"awawda.sanaa@yahoo.com"
    msg['Date'] = email.utils.formatdate(localtime=False)
    
    domain = GMAIL_ADDRESS.split('@')[1] if GMAIL_ADDRESS and '@' in GMAIL_ADDRESS else 'gmail.com'
    msg['Message-ID'] = email.utils.make_msgid(domain=domain)
    
    part1 = MIMEText("Your August 2026 report is attached as HTML in this email. Please open in a modern mail client to view.", 'plain', 'utf-8')
    part2 = MIMEText(html_content, 'html', 'utf-8')
    
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("Success! Sent HTML email.")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == '__main__':
    run()
