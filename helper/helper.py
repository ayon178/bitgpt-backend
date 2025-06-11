import httpx
import random
from fastapi import BackgroundTasks
from typing import Optional
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)


import re

def generate_slug(title: str) -> str:
    slug = re.sub(r'\s+', '-', title.strip().lower())
    slug = re.sub(r'[^\w\-]', '', slug)
    return slug

# Load env vars at module level
# from core.config import SMS_API_KEY, SMS_SENDER_ID, SMS_API_URL


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


async def send_otp(phone: str, otp: str):
    """
    Send OTP via SMS with full response logging.
    Handles encoding issues gracefully.
    """

    # Step 1: Normalize phone number
    phone = phone.strip()
    if not phone.startswith("88"):
        phone = "88" + phone

    message = f"Your Tutor OTP is {otp}. Please verify within 5 minutes."

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://sms.mram.com.bd/smsapi",
                data={
                    "api_key": "C3001490665ea58e155540.07243709",
                    "type": "text",
                    "contacts": phone,
                    "senderid": "8809601014245",
                    "msg": message
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # 🔍 Log full response to debug why SMS isn't coming
            print(f"[SMS] Status Code: {response.status_code}")
            print(f"[SMS] Response Text: {response.text}")

            if response.status_code != 200:
                logger.error(f"[SMS] Failed to send OTP. Status: {response.status_code}, Response: {response.text[:200]}")
                raise Exception(f"SMS API failed: {response.status_code} - {response.text}")

            logger.info(f"[SMS] Sent OTP to {phone}")
            return True

        except UnicodeEncodeError as e:
            logger.warning(f"[SMS] Encoding error: {str(e)}")
            return True

        except Exception as e:
            logger.exception("[SMS] Unexpected error sending OTP:")
            raise