from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from .config import settings

mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False  # TODO - Only set to False for local debugging!
)

fm = FastMail(mail_config)

async def send_verification_email(to_email: str, token: str):
    verify_url = f"{settings.frontend_url}/verify-email?token={token}"

    body = f"""
    <h2>Verify your email</h2>
    <p>Click the link below to activate your account. This link expires in 24 hours.</p>
    <a href="{verify_url}" style="
        display:inline-block;padding:12px 24px;
        background:#5B4EE8;color:white;
        border-radius:6px;text-decoration:none;font-weight:600;
    ">Verify email</a>
    <p style="color:#888;font-size:13px;margin-top:24px;">
        Or copy this link: {verify_url}
    </p>
    """

    message = MessageSchema(
        subject="Verify your email address",
        recipients=[to_email],
        body=body,
        subtype=MessageType.html,
    )
    await fm.send_message(message)


async def send_already_verified_email(to_email: str):
    """Friendly notice when someone tries to verify a second time."""
    message = MessageSchema(
        subject="Your email is already verified",
        recipients=[to_email],
        body="<p>Your account is already verified. You can log in normally.</p>",
        subtype=MessageType.html,
    )
    await fm.send_message(message)