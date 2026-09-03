from pathlib import Path
from datetime import datetime
import csv
import uuid


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

AUDIT_FILE = DATA_DIR / "audit_log.csv"

AUDIT_FIELDS = [
    "audit_id",
    "payment_id",
    "customer_name",
    "amount",
    "action",
    "event",
    "status",
    "payment_link_id",
    "payment_link",
    "reference_id",
    "created_at",
    "updated_at",
]


def load_audit_records():
    """
    Load payment audit records from audit_log.csv.
    """
    if not AUDIT_FILE.exists():
        return []

    try:
        with open(
            AUDIT_FILE,
            mode="r",
            newline="",
            encoding="utf-8",
        ) as file:
            return list(csv.DictReader(file))

    except Exception as error:
        print(f"Error loading audit records: {error}")
        return []


def save_audit_record(record):
    """
    Append one payment audit record to audit_log.csv.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    file_exists = AUDIT_FILE.exists()
    file_is_empty = (
        file_exists
        and AUDIT_FILE.stat().st_size == 0
    )

    now = datetime.now().isoformat()

    audit_record = {
        "audit_id": record.get(
            "audit_id",
            str(uuid.uuid4()),
        ),
        "payment_id": record.get(
            "payment_id",
            "",
        ),
        "customer_name": record.get(
            "customer_name",
            record.get("customer", ""),
        ),
        "amount": record.get(
            "amount",
            "",
        ),
        "action": record.get(
            "action",
            "",
        ),
        "event": record.get(
            "event",
            "",
        ),
        "status": record.get(
            "status",
            "created",
        ),
        "payment_link_id": record.get(
            "payment_link_id",
            "",
        ),
        "payment_link": record.get(
            "payment_link",
            record.get("short_url", ""),
        ),
        "reference_id": record.get(
            "reference_id",
            "",
        ),
        "created_at": record.get(
            "created_at",
            now,
        ),
        "updated_at": record.get(
            "updated_at",
            now,
        ),
    }

    with open(
        AUDIT_FILE,
        mode="a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=AUDIT_FIELDS,
        )

        if not file_exists or file_is_empty:
            writer.writeheader()

        writer.writerow(audit_record)

    return True


def create_audit_record(payment, link_data=None):
    """
    Create an audit record for a payment-link operation.
    """
    link_data = link_data or {}

    return {
        "audit_id": str(uuid.uuid4()),
        "payment_id": payment.get(
            "payment_id",
            "",
        ),
        "customer_name": (
            payment.get("customer_name")
            or payment.get("customer")
            or ""
        ),
        "amount": (
            payment.get("amount")
            or payment.get("recovery_amount")
            or ""
        ),
        "action": "create_payment_link",
        "event": "payment_link_created",
        "status": link_data.get(
            "status",
            "created",
        ),
        "payment_link_id": link_data.get(
            "payment_link_id",
            link_data.get("id", ""),
        ),
        "payment_link": link_data.get(
            "payment_link",
            link_data.get("short_url", ""),
        ),
        "reference_id": link_data.get(
            "reference_id",
            "",
        ),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def update_audit_status(payment_link_id, status):
    """
    Update the status of all matching payment-link audit records.
    """
    records = load_audit_records()
    updated = False

    for record in records:
        if record.get("payment_link_id") == payment_link_id:
            record["status"] = status
            record["updated_at"] = datetime.now().isoformat()
            updated = True

    if updated:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(
            AUDIT_FILE,
            mode="w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=AUDIT_FIELDS,
            )

            writer.writeheader()
            writer.writerows(records)

    return updated


def reset_audit_file():
    """
    Clear the payment audit file.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(
        AUDIT_FILE,
        mode="w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=AUDIT_FIELDS,
        )

        writer.writeheader()

    return True