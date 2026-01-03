import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
FROM_EMAIL = os.getenv("FROM_EMAIL")

def send_email(to: str, subject: str, body: str):
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to,
        subject=subject,
        plain_text_content=body
    )
    sg.send(message)
