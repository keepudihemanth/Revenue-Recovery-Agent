from pathlib import Path
from datetime import datetime
import csv


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RECEIVABLES_FILE = DATA_DIR / "receivables.csv"
RECEIVABLES_AUDIT_FILE = DATA_DIR / "receivables_audit.csv"


RECEIVABLES_AUDIT_FIELDS = [
    "invoice_id",
    "company",
    "amount",
    "risk_level",
    "recommended_action",
    "executed_action",
    "status",
    "created_at",
]


def read_csv_file(file_path):
    if not file_path.exists():
        return []

    with open(
        file_path,
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def append_audit_record(record):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    file_exists = RECEIVABLES_AUDIT_FILE.exists()
    is_empty = (
        file_exists
        and RECEIVABLES_AUDIT_FILE.stat().st_size == 0
    )

    with open(
        RECEIVABLES_AUDIT_FILE,
        mode="a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=RECEIVABLES_AUDIT_FIELDS,
        )

        if not file_exists or is_empty:
            writer.writeheader()

        writer.writerow(
            {
                field: record.get(field, "")
                for field in RECEIVABLES_AUDIT_FIELDS
            }
        )


def get_receivables():
    records = read_csv_file(RECEIVABLES_FILE)

    for record in records:
        try:
            record["amount"] = float(
                record.get("amount", 0)
            )
        except (TypeError, ValueError):
            record["amount"] = 0.0

        record["invoice_id"] = (
            record.get("invoice_id") or ""
        )

        record["company"] = (
            record.get("company") or ""
        )

        record["risk_level"] = (
            record.get("risk_level") or "low"
        )

        record["recommended_action"] = (
            record.get("recommended_action")
            or "no_action"
        )

        record["status"] = (
            record.get("status") or "open"
        )

    return records


def get_receivables_summary():
    records = get_receivables()

    total_receivables = len(records)

    total_amount = sum(
        float(record.get("amount", 0))
        for record in records
    )

    overdue_count = sum(
        1
        for record in records
        if str(record.get("status", "")).lower()
        == "overdue"
    )

    high_risk_count = sum(
        1
        for record in records
        if str(record.get("risk_level", "")).lower()
        == "high"
    )

    return {
        "total_receivables": total_receivables,
        "total_amount": total_amount,
        "overdue_count": overdue_count,
        "high_risk_count": high_risk_count,
    }


def find_receivable(invoice_id):
    records = get_receivables()

    return next(
        (
            record
            for record in records
            if str(record.get("invoice_id", ""))
            == str(invoice_id)
        ),
        None,
    )


def execute_receivable_action(invoice_id):
    receivable = find_receivable(invoice_id)

    if receivable is None:
        raise ValueError(
            f"Receivable {invoice_id} was not found"
        )

    recommended_action = (
        receivable.get("recommended_action")
        or "no_action"
    )

    append_audit_record(
        {
            "invoice_id": invoice_id,
            "company": receivable.get("company", ""),
            "amount": receivable.get("amount", 0),
            "risk_level": receivable.get("risk_level", ""),
            "recommended_action": recommended_action,
            "executed_action": recommended_action,
            "status": "executed",
            "created_at": datetime.now().isoformat(),
        }
    )

    return {
        "invoice_id": invoice_id,
        "action": recommended_action,
        "status": "executed",
        "message": (
            f"Action '{recommended_action}' "
            f"executed for {invoice_id}"
        ),
    }


def record_promise_to_pay(invoice_id):
    receivable = find_receivable(invoice_id)

    if receivable is None:
        raise ValueError(
            f"Receivable {invoice_id} was not found"
        )

    append_audit_record(
        {
            "invoice_id": invoice_id,
            "company": receivable.get("company", ""),
            "amount": receivable.get("amount", 0),
            "risk_level": receivable.get("risk_level", ""),
            "recommended_action": receivable.get(
                "recommended_action",
                "",
            ),
            "executed_action": "record_promise",
            "status": "promise_recorded",
            "created_at": datetime.now().isoformat(),
        }
    )

    return {
        "invoice_id": invoice_id,
        "action": "record_promise",
        "status": "promise_to_pay",
        "message": (
            f"Promise to pay recorded for {invoice_id}"
        ),
    }