import traceback

from flask import Flask, jsonify, request
from flask_cors import CORS

from razorpay_service import get_payment_link_status
from recovery_engine import (
    load_payments,
    analyze_payment,
    sync_payment_link_status,
    reset_payments,
)

from receivables_engine import (
    get_receivables,
    get_receivables_summary,
    execute_receivable_action,
    record_promise_to_pay,
)

from audit import (
    load_audit_records,
    save_audit_record,
    create_audit_record,
    update_audit_status,
    reset_audit_file,
)

from receivables_audit import load_receivables_audit


app = Flask(__name__)


CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        }
    },
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# =========================================================
# Helpers
# =========================================================

def json_error(message, status_code=400):
    return jsonify({
        "success": False,
        "error": message,
    }), status_code


def get_latest_audit_for_payment(payment_id):
    """
    Return the latest audit record for a payment.
    """
    records = load_audit_records()

    matching_records = [
        record
        for record in records
        if str(record.get("payment_id", "")).strip()
        == str(payment_id).strip()
    ]

    if not matching_records:
        return None

    return matching_records[-1]


def get_analyzed_payments():
    """
    Load payments and apply the latest audit status.
    """
    payments = load_payments()
    analyzed_payments = []

    for payment in payments:
        analyzed_payment = analyze_payment(payment)

        payment_id = str(
            payment.get("payment_id", "")
        ).strip()

        audit_record = get_latest_audit_for_payment(
            payment_id
        )

        if audit_record:
            audit_status = str(
                audit_record.get("status", "")
            ).strip().lower()

            if audit_status == "recovered":
                analyzed_payment["status"] = "recovered"
                analyzed_payment["recovery_status"] = "recovered"

            elif audit_status == "failed":
                analyzed_payment["recovery_status"] = "failed"

            elif audit_status == "pending":
                analyzed_payment["recovery_status"] = "pending"

        analyzed_payments.append(analyzed_payment)

    return analyzed_payments


def find_payment(payment_id):
    """
    Find one analyzed payment by payment_id.
    """
    payments = get_analyzed_payments()

    return next(
        (
            payment
            for payment in payments
            if str(payment.get("payment_id", "")).strip()
            == str(payment_id).strip()
        ),
        None,
    )


def get_razorpay_service():
    """
    Import Razorpay operations only when required.
    """
    from razorpay_service import (
        create_payment_link,
        get_payment_link_status,
    )

    return create_payment_link, get_payment_link_status


# =========================================================
# Health
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "success": True,
        "message": "Revenue Recovery Backend is running",
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "success": True,
        "message": "Backend is healthy",
    })


# =========================================================
# Recovery queue
# =========================================================

@app.route("/api/recovery", methods=["GET"])
def recovery_queue():
    try:
        payments = get_analyzed_payments()
        result = []

        for payment in payments:
            item = dict(payment)

            payment_id = str(
                payment.get("payment_id", "")
            ).strip()

            audit_record = get_latest_audit_for_payment(
                payment_id
            )

            if audit_record:
                item["payment_link_id"] = (
                    audit_record.get("payment_link_id", "")
                )

                item["payment_link"] = (
                    audit_record.get("payment_link", "")
                )

                item["recovery_status"] = (
                    audit_record.get("status", "pending")
                )

            else:
                item["payment_link_id"] = ""
                item["payment_link"] = ""

                item["recovery_status"] = (
                    "recovered"
                    if str(
                        item.get("status", "")
                    ).lower() == "recovered"
                    else "pending"
                )

            result.append(item)

        return jsonify({
            "success": True,
            "count": len(result),
            "payments": result,
            "data": result,
        }), 200

    except Exception as error:
        traceback.print_exc()
        return json_error(str(error), 500)


# =========================================================
# Recovery action
# =========================================================

@app.route(
    "/api/payments/<payment_id>/recover",
    methods=["POST"],
)
def recover_payment(payment_id):
    """
    Execute the recommended recovery action.

    For create_payment_link:
        Create a Razorpay payment link and keep the
        payment pending until it is actually paid.

    For other actions:
        Return the recommended action without falsely
        marking the payment as recovered.
    """

    try:
        payment = find_payment(payment_id)

        if payment is None:
            return json_error(
                f"Payment {payment_id} not found",
                404,
            )

        action = str(
            payment.get("action", "")
        ).strip().lower()

        # -------------------------------------------------
        # Create Razorpay payment link
        # -------------------------------------------------

        if action == "create_payment_link":
            try:
                create_payment_link, _ = (
                    get_razorpay_service()
                )

            except Exception as error:
                return jsonify({
                    "success": False,
                    "message": (
                        "Razorpay is not configured. "
                        "Check RAZORPAY_KEY_ID and "
                        "RAZORPAY_KEY_SECRET in .env."
                    ),
                    "error": str(error),
                }), 503

            body = request.get_json(silent=True) or {}

            customer_name = (
                body.get("customer_name")
                or payment.get("customer_name")
                or payment.get("customer")
                or "Customer"
            )

            customer_email = (
                body.get("customer_email")
                or payment.get("customer_email")
                or payment.get("email")
                or ""
            )

            amount = (
                payment.get("amount")
                or payment.get("recovery_amount")
                or 0
            )

            link_data = create_payment_link(
                amount=amount,
                customer_name=customer_name,
                customer_email=customer_email,
                payment_id=payment_id,
            )

            audit_record = create_audit_record(
                payment,
                link_data,
            )

            save_audit_record(audit_record)

            return jsonify({
                "success": True,
                "message": "Razorpay payment link created",
                "payment_id": payment_id,
                "action": "create_payment_link",
                "status": "pending",
                "recovery_status": "pending",
                "payment_link_id": link_data.get(
                    "payment_link_id",
                    "",
                ),
                "payment_link": link_data.get(
                    "payment_link",
                    "",
                ),
                "reference_id": link_data.get(
                    "reference_id",
                    "",
                ),
            }), 200

        # -------------------------------------------------
        # Other recovery actions
        # -------------------------------------------------

        return jsonify({
            "success": True,
            "message": "Recovery action is pending execution",
            "payment_id": payment_id,
            "action": action,
            "status": payment.get("status"),
            "recovery_status": "pending",
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Check Razorpay payment-link status
# =========================================================

@app.route(
    "/api/payment-links/<payment_link_id>",
    methods=["GET"],
)
def check_payment_link(payment_link_id):
    try:
        _, get_payment_link_status = (
            get_razorpay_service()
        )

        result = get_payment_link_status(
            payment_link_id
        )

        return jsonify({
            "success": True,
            "payment_link": result,
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Synchronize Razorpay payment-link status
# =========================================================

@app.route(
    "/api/payment-links/<payment_link_id>/sync",
    methods=["POST"],
)
def sync_payment_link(payment_link_id):
    """
    Fetch the current Razorpay Payment Link status and
    synchronize the matching local payment and audit records.
    """

    try:
        _, get_payment_link_status = (
            get_razorpay_service()
        )

        # -------------------------------------------------
        # 1. Fetch the current status from Razorpay
        # -------------------------------------------------

        razorpay_data = get_payment_link_status(
            payment_link_id
        )

        razorpay_status = str(
            razorpay_data.get("status", "")
        ).strip().lower()

        # -------------------------------------------------
        # 2. Find the local payment_id from audit_log.csv
        # -------------------------------------------------

        audit_records = load_audit_records()
        payment_id = None

        for record in audit_records:
            stored_link_id = str(
                record.get("payment_link_id") or ""
            ).strip()

            if stored_link_id == str(
                payment_link_id
            ).strip():
                payment_id = str(
                    record.get("payment_id") or ""
                ).strip()
                break

        if not payment_id:
            return json_error(
                "No audit record found for payment link "
                f"{payment_link_id}",
                404,
            )

        # -------------------------------------------------
        # 3. Update payments.csv using payment_id
        # -------------------------------------------------

        payment_result = sync_payment_link_status(
            payment_id=payment_id,
            razorpay_status=razorpay_status,
        )

        # -------------------------------------------------
        # 4. Convert Razorpay status to audit status
        # -------------------------------------------------

        if razorpay_status in {
            "paid",
            "captured",
            "success",
            "successful",
        }:
            audit_status = "recovered"

        elif razorpay_status in {
            "failed",
            "cancelled",
            "canceled",
            "expired",
        }:
            audit_status = "failed"

        else:
            audit_status = "pending"

        # -------------------------------------------------
        # 5. Update audit_log.csv
        # -------------------------------------------------

        update_audit_status(
            payment_link_id,
            audit_status,
        )

        # -------------------------------------------------
        # 6. Return synchronized result
        # -------------------------------------------------

        return jsonify({
            "success": True,
            "razorpay_status": razorpay_status,
            "audit_status": audit_status,
            "payment": payment_result,
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Create recovery payment link
# =========================================================

@app.route(
    "/api/recovery/create-link/<payment_id>",
    methods=["POST"],
)
def create_recovery_link(payment_id):
    try:
        payment = find_payment(payment_id)

        if payment is None:
            return json_error(
                f"Payment {payment_id} not found",
                404,
            )

        if payment.get("action") != "create_payment_link":
            return json_error(
                f"Payment {payment_id} is not eligible "
                "for a payment link",
                400,
            )

        try:
            create_payment_link, _ = (
                get_razorpay_service()
            )

        except Exception as error:
            return jsonify({
                "success": False,
                "message": (
                    "Razorpay is not configured. "
                    "Check your .env credentials."
                ),
                "error": str(error),
            }), 503

        body = request.get_json(silent=True) or {}

        customer_name = (
            body.get("customer_name")
            or payment.get("customer_name")
            or payment.get("customer")
            or "Customer"
        )

        customer_email = (
            body.get("customer_email")
            or payment.get("customer_email")
            or payment.get("email")
            or ""
        )

        amount = (
            payment.get("amount")
            or payment.get("recovery_amount")
            or 0
        )

        link_data = create_payment_link(
            amount=amount,
            customer_name=customer_name,
            customer_email=customer_email,
            payment_id=payment_id,
        )

        audit_record = create_audit_record(
            payment,
            link_data,
        )

        save_audit_record(audit_record)

        return jsonify({
            "success": True,
            "message": "Razorpay payment link created",
            "payment_id": payment_id,
            "action": "create_payment_link",
            "status": "pending",
            "recovery_status": "pending",
            "payment_link_id": link_data.get(
                "payment_link_id",
                "",
            ),
            "payment_link": link_data.get(
                "payment_link",
                "",
            ),
            "short_url": link_data.get(
                "payment_link",
                "",
            ),
            "reference_id": link_data.get(
                "reference_id",
                "",
            ),
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Razorpay payment-link status and audit update
# =========================================================

@app.route(
    "/api/recovery/status/<payment_link_id>",
    methods=["GET"],
)
def recovery_status(payment_link_id):
    try:
        _, get_payment_link_status = (
            get_razorpay_service()
        )

        status_data = get_payment_link_status(
            payment_link_id
        )

        razorpay_status = str(
            status_data.get("status", "")
        ).lower()

        if razorpay_status in {
            "paid",
            "captured",
            "success",
            "successful",
        }:
            audit_status = "recovered"

        elif razorpay_status in {
            "failed",
            "cancelled",
            "canceled",
            "expired",
        }:
            audit_status = "failed"

        else:
            audit_status = "pending"

        updated = update_audit_status(
            payment_link_id,
            audit_status,
        )

        return jsonify({
            "success": True,
            "payment_link_id": payment_link_id,
            "razorpay_status": razorpay_status,
            "audit_status": audit_status,
            "status": audit_status,
            "updated": updated,
            "payment": status_data,
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


@app.route(
    "/api/recovery/status/<payment_link_id>/update-audit",
    methods=["POST"],
)
def update_recovery_audit(payment_link_id):
    return recovery_status(payment_link_id)


# =========================================================
# Payment audit
# =========================================================

@app.route("/api/audit", methods=["GET"])
def audit_history():
    try:
        records = load_audit_records()

        return jsonify({
            "success": True,
            "count": len(records),
            "records": records,
            "data": records,
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Recovery summary
# =========================================================

@app.route("/api/summary", methods=["GET"])
def recovery_summary():
    try:
        payments = get_analyzed_payments()

        total_amount = sum(
            float(payment.get("amount", 0) or 0)
            for payment in payments
        )

        recovered_amount = sum(
            float(payment.get("amount", 0) or 0)
            for payment in payments
            if (
                str(
                    payment.get("status", "")
                ).lower()
                in {
                    "recovered",
                    "paid",
                    "captured",
                    "success",
                    "successful",
                }
                or
                str(
                    payment.get("recovery_status", "")
                ).lower()
                in {
                    "recovered",
                    "paid",
                    "captured",
                    "success",
                    "successful",
                }
            )
        )

        pending_amount = max(
            total_amount - recovered_amount,
            0,
        )

        recovery_rate = (
            recovered_amount / total_amount * 100
            if total_amount > 0
            else 0
        )

        summary = {
            "total_payments": len(payments),
            "total_amount": total_amount,
            "recoverable_amount": pending_amount,
            "recovered_amount": recovered_amount,
            "pending_amount": pending_amount,
            "recovery_rate": recovery_rate,
        }

        return jsonify({
            "success": True,
            "summary": summary,
            **summary,
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Reset demo
# =========================================================

@app.route("/api/demo/reset", methods=["POST"])
def reset_demo():
    try:
        reset_audit_file()
        reset_payments()

        return jsonify({
            "success": True,
            "message": "Demo data reset successfully",
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Receivables queue
# =========================================================

@app.route("/api/receivables", methods=["GET"])
def receivables_queue():
    try:
        records = get_receivables()

        return jsonify({
            "success": True,
            "count": len(records),
            "receivables": records,
            "data": records,
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


@app.route("/api/receivables/summary", methods=["GET"])
def receivables_summary():
    try:
        summary = get_receivables_summary()

        return jsonify({
            "success": True,
            "summary": summary,
            **summary,
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Execute receivable action
# =========================================================

def execute_receivable(invoice_id):
    result = execute_receivable_action(
        invoice_id
    )

    return jsonify({
        "success": True,
        **result,
    }), 200


@app.route(
    "/api/receivables/execute/<invoice_id>",
    methods=["POST"],
)
def execute_receivable_frontend(invoice_id):
    try:
        return execute_receivable(invoice_id)

    except ValueError as error:
        return json_error(
            str(error),
            404,
        )

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


@app.route(
    "/api/receivables/<invoice_id>/execute",
    methods=["POST"],
)
def execute_receivable_alternate(invoice_id):
    return execute_receivable_frontend(invoice_id)


# =========================================================
# Promise to pay
# =========================================================

@app.route(
    "/api/receivables/promise/<invoice_id>",
    methods=["POST"],
)
def promise_to_pay(invoice_id):
    try:
        result = record_promise_to_pay(
            invoice_id
        )

        return jsonify({
            "success": True,
            **result,
        }), 200

    except ValueError as error:
        return json_error(
            str(error),
            404,
        )

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Receivables audit history
# =========================================================

@app.route("/api/receivables-audit", methods=["GET"])
def receivables_audit_history():
    try:
        records = load_receivables_audit()

        return jsonify({
            "success": True,
            "count": len(records),
            "records": records,
            "data": records,
        }), 200

    except Exception as error:
        traceback.print_exc()

        return json_error(
            str(error),
            500,
        )


# =========================================================
# Error handlers
# =========================================================

@app.errorhandler(404)
def not_found(error):
    return json_error(
        "Route not found",
        404,
    )


@app.errorhandler(405)
def method_not_allowed(error):
    return json_error(
        "HTTP method not allowed",
        405,
    )


# =========================================================
# Run application
# =========================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )