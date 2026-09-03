import os
from dotenv import load_dotenv
import razorpay

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise RuntimeError(
        "Missing RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET in backend/.env"
    )

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)


def create_payment_link(
    amount,
    customer_name,
    customer_email,
    payment_id,
):
    amount_in_paise = int(float(amount) * 100)

    payment_link = razorpay_client.payment_link.create(
        {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": f"Revenue recovery for {payment_id}",
            "customer": {
                "name": customer_name,
                "email": customer_email,
            },
            "notify": {
                "email": True,
                "sms": False,
            },
            "reminder_enable": True,
            "notes": {
                "payment_id": str(payment_id),
                "recovery_type": "revenue_recovery",
            },
        }
    )

    return {
        "payment_link_id": payment_link.get("id", ""),
        "payment_link": payment_link.get("short_url", ""),
        "status": payment_link.get("status", "created"),
        "amount": payment_link.get("amount", 0),
        "reference_id": payment_link.get("reference_id", ""),
    }


def get_payment_link_status(payment_link_id):
    payment_link = razorpay_client.payment_link.fetch(
        payment_link_id
    )

    return {
        "id": payment_link.get("id", ""),
        "status": str(payment_link.get("status", "")).lower(),
        "amount": payment_link.get("amount", 0),
        "short_url": payment_link.get("short_url", ""),
        "reference_id": payment_link.get("reference_id", ""),
        "payments": payment_link.get("payments", []),
    }