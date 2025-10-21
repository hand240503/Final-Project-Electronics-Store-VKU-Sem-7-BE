# utils/email_utils.py

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv


import random
from django.core.mail import send_mail
from django.conf import settings
# Load biến môi trường từ .env
load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Gửi email cơ bản sử dụng SMTP, lấy cấu hình từ .env.
    - to_email: địa chỉ người nhận
    - subject: tiêu đề email
    - body: nội dung email (có thể HTML)
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_HOST_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        # Kết nối SMTP
        if EMAIL_USE_TLS:
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT)

        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False



def send_otp_email(to_email, otp):
    subject = "Your Registration OTP"
    message = f"Your OTP for registration is: {otp}. It is valid for 5 minutes."
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [to_email],
        fail_silently=False,
    )

