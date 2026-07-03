import smtplib
import os
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils.logger import logger

load_dotenv()

SMTP_KEY=os.getenv("SMTP_KEY")
SMTP_LOGIN=os.getenv("SMTP_LOGIN")
SMTP_PORT=os.getenv("SMTP_PORT")
SMTP_SERVER=os.getenv("SMTP_SERVER")


def get_html_with_code(otp:int) -> str:
    return f"""\
    <!DOCTYPE html>
    <html>
    <body style="font-family: sans-serif; padding: 20px; color: #333;">
        <h3>Verify your email</h3>
        <p>Use this code to complete registration:</p>
        <div style="font-size: 28px; font-weight: bold; background: #f0f0f0; padding: 10px; width: fit-content; letter-spacing: 2px;">
            {otp}
        </div>
        <p style="font-size: 12px; color: #666;">Expires in 3 minutes.</p>
    </body>
    </html>
    """

def send_email(
                otp:int,
                user_email:str
                ) -> None:
    plain_text='Email verification code.'

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your email verification code!"
    msg["From"] = SMTP_LOGIN
    msg["To"] = user_email
    html_content = get_html_with_code(otp)
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_KEY)
            server.send_message(msg)
        logger.info(f"Verification email to {user_email} was sent with code {otp}.")
    except Exception as ex:
        logger.error(f"Failed to send an email, error:{ex}.")
    

