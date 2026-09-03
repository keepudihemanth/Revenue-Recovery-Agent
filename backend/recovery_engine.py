import os
import shutil
import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PAYMENTS_FILE = BASE_DIR / "data" / "payments.csv"


def load_payments():
    """
    Load payment records from payments.csv.
    """
    if not PAYMENTS_FILE.exists():
        return []

    with open(
        PAYMENTS_FILE,
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))

def process_recovery_batch():
    """
    Load all payments and analyze each payment.
    """
    payments = load_payments()

    return [
        analyze_payment(payment)
        for payment in payments
    ]

def save_payments(payments):
    """
    Save payment records to payments.csv.
    """
    PAYMENTS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not payments:
        return

    fieldnames = list(payments[0].keys())

    with open(
        PAYMENTS_FILE,
        mode="w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(payments)


def to_float(value):
    """
    Safely convert a value to float.
    """
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def to_int(value):
    """
    Safely convert a value to int.
    """
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def analyze_payment(payment):
    """
    Analyze one payment and determine:
    - revenue at risk
    - risk level
    - recommended recovery action
    """

    payment_id = str(
        payment.get("payment_id")
        or payment.get("id")
        or ""
    )

    customer_name = (
        payment.get("customer_name")
        or payment.get("customer")
        or "Unknown customer"
    )

    amount = to_float(
        payment.get("amount")
        or payment.get("recovery_amount")
        or payment.get("revenue_at_risk")
        or 0
    )

    attempts = to_int(
        payment.get("attempts")
        or payment.get("retry_count")
        or 0
    )

    failure_reason = str(
        payment.get("failure_reason")
        or payment.get("reason")
        or payment.get("status")
        or ""
    ).strip().lower()

    payment_status = str(
        payment.get("status")
        or ""
    ).strip().lower()

    if payment_status in {
        "paid",
        "captured",
        "success",
        "successful",
        "recovered",
    }:
        risk_level = "low"
        action = "no_action"

    elif attempts >= 2:
        risk_level = "high"
        action = "escalate"

    elif failure_reason in {
        "checkout_abandoned",
        "checkout abandoned",
        "abandoned",
        "payment_link_expired",
    }:
        risk_level = "high"
        action = "create_payment_link"

    elif failure_reason in {
        "temporary_failure",
        "temporary failure",
        "timeout",
        "gateway_timeout",
        "network_error",
        "technical_failure",
    }:
        risk_level = "medium"
        action = "retry_payment"

    elif failure_reason in {
        "insufficient_funds",
        "insufficient funds",
        "bank_declined",
        "bank declined",
        "card_declined",
        "card declined",
    }:
        risk_level = "medium"
        action = "send_reminder"

    elif failure_reason in {
        "fraud",
        "suspected_fraud",
        "suspected fraud",
        "authentication_failed",
        "authentication failed",
    }:
        risk_level = "high"
        action = "escalate"

    else:
        risk_level = "medium"
        action = "send_reminder"

    return {
        **payment,
        "payment_id": payment_id,
        "customer_name": customer_name,
        "amount": amount,
        "recovery_amount": amount,
        "revenue_at_risk": amount,
        "attempts": attempts,
        "failure_reason": failure_reason,
        "risk_level": risk_level,
        "action": action,
    }


def update_payment_status(payment_id, new_status):
    """
    Update the status of one payment.
    """
    payments = load_payments()

    for payment in payments:
        current_payment_id = str(
            payment.get("payment_id")
            or payment.get("id")
            or ""
        )

        if current_payment_id == str(payment_id):
            payment["status"] = new_status
            save_payments(payments)

            return {
                "payment_id": payment_id,
                "status": new_status,
                "message": (
                    "Payment status updated successfully"
                ),
            }

    raise ValueError(
        f"Payment {payment_id} was not found"
    )
def sync_payment_link_status(
    payment_id,
    razorpay_status,
):
    """
    Update a local payment using its payment_id
    after checking the Razorpay Payment Link status.
    """

    status = str(
        razorpay_status or ""
    ).strip().lower()

    if status in {
        "paid",
        "captured",
        "success",
        "successful",
    }:
        new_status = "recovered"
        recovery_status = "recovered"

    elif status in {
        "expired",
        "cancelled",
        "canceled",
    }:
        new_status = "failed"
        recovery_status = "pending"

    else:
        new_status = "pending"
        recovery_status = "pending"

    payments = load_payments()
    updated_payment = None

    for payment in payments:
        current_payment_id = str(
            payment.get("payment_id")
            or payment.get("id")
            or ""
        ).strip()

        if current_payment_id == str(
            payment_id
        ).strip():

            payment["status"] = new_status
            payment["recovery_status"] = recovery_status

            if new_status == "recovered":
                payment["failure_reason"] = ""

            updated_payment = payment
            break

    if updated_payment is None:
        raise ValueError(
            f"Payment {payment_id} was not found in payments.csv"
        )

    save_payments(payments)

    return {
        "payment_id": updated_payment.get(
            "payment_id",
            "",
        ),
        "status": new_status,
        "recovery_status": recovery_status,
    }
def reset_payments():
    backup_file = "data/payments_demo_backup.csv"

    if not os.path.exists(backup_file):
        raise FileNotFoundError(
            f"Demo backup file not found: {backup_file}"
        )

    shutil.copyfile(backup_file, PAYMENTS_FILE)

    return load_payments()
    return load_payments()