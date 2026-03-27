"""
send.py — Deliver the digest email via Resend SDK.
"""

import logging
import os
import time
from datetime import datetime, timezone

import resend

logger = logging.getLogger(__name__)


def send_email(
    html_body: str,
    text_body: str,
    resend_api_key: str,
    recipient_email: str,
    from_email: str = "Daily Brief <digest@yourdomain.com>",
) -> bool:
    """Send the digest email via Resend SDK. Returns True on success."""
    resend.api_key = resend_api_key

    now = datetime.now(tz=timezone.utc)
    subject = f"📰 Daily Brief — {now.strftime('%A, %B %-d')}"

    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": [recipient_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    logger.info(
        f"Resend → from={from_email!r} to={recipient_email!r} subject={subject!r}"
    )
    logger.info(
        f"Resend → payload size: {len(html_body):,} bytes  key=...{resend_api_key[-6:]}"
    )

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Resend → attempt {attempt}/{max_attempts}")
        try:
            result = resend.Emails.send(params)
            logger.info(f"Resend → delivered  id={result.get('id')!r}")
            return True
        except resend.exceptions.ResendError as e:
            logger.error(f"Resend → API error ({type(e).__name__}): {e}")
            # Non-retryable: auth failure, domain not verified, bad payload
            if hasattr(e, "status_code") and e.status_code not in (
                429,
                500,
                502,
                503,
                504,
            ):
                return False
        except Exception as e:
            logger.error(f"Resend → unexpected error ({type(e).__name__}): {e}")

        if attempt < max_attempts:
            wait = 2**attempt  # 2s, 4s
            logger.info(f"Resend → retrying in {wait}s...")
            time.sleep(wait)

    logger.error(f"Resend → delivery failed after {max_attempts} attempts")
    return False


if __name__ == "__main__":
    import sys

    html = sys.stdin.read()
    success = send_email(
        html_body=html,
        text_body="Plain text version not provided.",
        resend_api_key=os.environ["RESEND_API_KEY"],
        recipient_email=os.environ["RECIPIENT_EMAIL"],
    )
    sys.exit(0 if success else 1)
