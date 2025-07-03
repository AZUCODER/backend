import httpx
from app.config import get_settings

settings = get_settings()

RESEND_API_URL = "https://api.resend.com/emails"


async def send_email_via_resend(to_email: str, subject: str, html_body: str):
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": settings.FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(RESEND_API_URL, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise Exception(f"Failed to send email: {resp.status_code} {resp.text}")
        return resp.json()
