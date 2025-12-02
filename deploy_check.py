import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime

def send_deployment_email():
    sender_email = os.environ.get("EMAIL_USER")
    sender_password = os.environ.get("EMAIL_PASSWORD")
    receiver_email = "vojerkan@gmail.com"
    
    if not sender_email or not sender_password:
        print("Error: Email credentials not found.")
        return
        
    subject = "🚀 MIDNIGHT EXPRESS: DEPLOYMENT SUCCESSFUL"
    body = f"""
    SYSTEM STATUS REPORT
    --------------------
    Timestamp: {datetime.datetime.now()}
    Status: ONLINE
    Configuration: T+1 Efficient Frontier
    
    The Midnight Express bot has been successfully deployed to GitHub Actions.
    The "Midnight Hunter" is now active and will run daily at 09:50 TRT.
    
    Current Strategy:
    - Entry: 09:55
    - Exit: Next Day 18:05
    - Trigger: Z > 0.5 / Z < -0.5
    
    This is a one-time confirmation message.
    """
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"Deployment email sent to {receiver_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    send_deployment_email()
