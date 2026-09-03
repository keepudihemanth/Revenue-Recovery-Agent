import csv
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
AUDIT_FILE = (
    BASE_DIR
    / "data"
    / "receivables_audit.csv"
)

FIELDNAMES = [
    "invoice_id",
    "company",
    "amount",
    "risk_level",
    "recommended_action",
    "executed_action",
    "status",
    "created_at",
]


def load_receivables_audit():
    if not AUDIT_FILE.exists():
        return []

    with open(
        AUDIT_FILE,
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        return list(csv.DictReader(file))


def append_receivables_audit(
    invoice_id,
    company,
    amount,
    risk_level,
    recommended_action,
    executed_action,
    status,
):
    AUDIT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_exists = (
        AUDIT_FILE.exists()
        and AUDIT_FILE.stat().st_size > 0
    )

    with open(
        AUDIT_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "invoice_id": invoice_id,
            "company": company,
            "amount": amount,
            "risk_level": risk_level,
            "recommended_action": recommended_action,
            "executed_action": executed_action,
            "status": status,
            "created_at": datetime.now().isoformat(),
        })