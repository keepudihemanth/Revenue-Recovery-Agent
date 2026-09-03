import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:5000";

function formatCurrency(value) {
  const amount = Number(value || 0);

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatLabel(value) {
  if (!value) {
    return "-";
  }

  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function getStatusClass(status) {
  const normalizedStatus = String(status || "").toLowerCase();

  if (
    normalizedStatus.includes("recover") ||
    normalizedStatus.includes("executed") ||
    normalizedStatus.includes("promise") ||
    normalizedStatus.includes("paid") ||
    normalizedStatus.includes("captured") ||
    normalizedStatus.includes("success")
  ) {
    return "status-badge status-success";
  }

  if (
    normalizedStatus.includes("pending") ||
    normalizedStatus.includes("overdue") ||
    normalizedStatus.includes("created")
  ) {
    return "status-badge status-warning";
  }

  if (
    normalizedStatus.includes("failed") ||
    normalizedStatus.includes("cancel") ||
    normalizedStatus.includes("expired")
  ) {
    return "status-badge status-danger";
  }

  return "status-badge status-neutral";
}

function App() {
  const [activeTab, setActiveTab] = useState("recovery");

  const [payments, setPayments] = useState([]);
  const [receivables, setReceivables] = useState([]);
  const [auditRecords, setAuditRecords] = useState([]);

  const [summary, setSummary] = useState({
    total_amount: 0,
    recovered_amount: 0,
    pending_amount: 0,
    recoverable_amount: 0,
    recovery_rate: 0,
    total_payments: 0,
    total_audit_records: 0,
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [pollingPayment, setPollingPayment] = useState(null);
  const pollingRef = useRef(null);

  /*
   * Generic API helper.
   */
  async function fetchJson(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    const contentType = response.headers.get("content-type") || "";

    const data = contentType.includes("application/json")
      ? await response.json()
      : {};

    if (!response.ok || data.success === false) {
      throw new Error(
        data.message ||
          data.error ||
          `Request failed with status ${response.status}`
      );
    }

    return data;
  }

  /*
   * Load payment-recovery records.
   */
  const loadPayments = useCallback(async () => {
    const data = await fetchJson("/api/recovery");

    setPayments(
      data.payments ||
        data.records ||
        data.data ||
        []
    );
  }, []);

  /*
   * Load dashboard summary.
   *
   * The backend currently returns the values both at the root
   * and inside the summary object, so both formats are supported.
   */
  const loadSummary = useCallback(async () => {
    const data = await fetchJson("/api/summary");

    const source = data.summary || data;

    setSummary({
      total_amount:
        source.total_amount ??
        source.total_at_risk ??
        source.revenue_at_risk ??
        0,

      recovered_amount:
        source.recovered_amount ??
        0,

      pending_amount:
        source.pending_amount ??
        0,

      recoverable_amount:
        source.recoverable_amount ??
        0,

      recovery_rate:
        source.recovery_rate ??
        0,

      total_payments:
        source.total_payments ??
        0,

      total_audit_records:
        source.total_audit_records ??
        0,
    });
  }, []);

  /*
   * Load receivables.
   *
   * This remains optional because some backend versions
   * may not expose this endpoint.
   */
  const loadReceivables = useCallback(async () => {
    try {
      const data = await fetchJson("/api/receivables");

      setReceivables(
        data.receivables ||
          data.records ||
          data.data ||
          []
      );
    } catch (requestError) {
      console.warn(
        "Receivables could not be loaded:",
        requestError
      );

      setReceivables([]);
    }
  }, []);

  /*
   * Load audit records.
   */
  const loadAuditRecords = useCallback(async () => {
    const data = await fetchJson("/api/audit");

    setAuditRecords(
      data.records ||
        data.data ||
        []
    );
  }, []);

  /*
   * Refresh every dashboard section.
   */
  const refreshAllData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      await Promise.all([
        loadPayments(),
        loadSummary(),
        loadReceivables(),
        loadAuditRecords(),
      ]);
    } catch (requestError) {
      console.error(
        "Dashboard refresh failed:",
        requestError
      );

      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [
    loadPayments,
    loadSummary,
    loadReceivables,
    loadAuditRecords,
  ]);

  /*
   * Initial dashboard load.
   */
  useEffect(() => {
    refreshAllData();
  }, [refreshAllData]);

  /*
   * Refresh when the browser window receives focus.
   */
  useEffect(() => {
    const handleWindowFocus = () => {
      refreshAllData();
    };

    window.addEventListener(
      "focus",
      handleWindowFocus
    );

    return () => {
      window.removeEventListener(
        "focus",
        handleWindowFocus
      );
    };
  }, [refreshAllData]);

  /*
   * Poll Razorpay payment-link status after opening
   * a payment link.
   *
   * The backend endpoint should update payments.csv
   * and audit_log.csv when the payment is successful.
   */
  useEffect(() => {
    if (!pollingPayment) {
      return;
    }

    let cancelled = false;

    const checkPaymentStatus = async () => {
      try {
        const response = await fetchJson(
          `/api/payment-links/${pollingPayment.paymentLinkId}/sync`,
          {
            method: "POST",
          }
        );

        const status = String(
          response.razorpay_status ||
            response.audit_status ||
            response.recovery_status ||
            response.status ||
            ""
        ).toLowerCase();

        const isRecovered =
          response.success === true &&
          (
            status === "recovered" ||
            status === "paid" ||
            status === "captured" ||
            status === "successful" ||
            status === "success" ||
            response.updated === true
          );

        if (isRecovered && !cancelled) {
          setMessage(
            `Payment ${pollingPayment.paymentId} recovered successfully.`
          );

          setPollingPayment(null);

          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }

          /*
           * Reload the payment table, summary cards,
           * receivables, and audit log.
           */
          await refreshAllData();
        }
      } catch (requestError) {
        /*
         * Do not stop polling for a temporary request error.
         * The next polling attempt will try again.
         */
        console.error(
          "Payment status check failed:",
          requestError
        );
      }
    };

    // Check immediately instead of waiting five seconds.
    checkPaymentStatus();

    // Continue checking every five seconds.
    pollingRef.current = setInterval(
      checkPaymentStatus,
      5000
    );

    return () => {
      cancelled = true;

      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [pollingPayment, refreshAllData]);

  /*
   * Execute a receivables action.
   */
  async function handleExecuteAction(invoiceId) {
    try {
      setLoading(true);
      setMessage("");
      setError("");

      const data = await fetchJson(
        `/api/receivables/execute/${invoiceId}`,
        {
          method: "POST",
        }
      );

      setMessage(
        data.message ||
          `Action executed for ${invoiceId}`
      );

      await refreshAllData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  /*
   * Record a promise to pay.
   */
  async function handlePromiseToPay(invoiceId) {
    try {
      setLoading(true);
      setMessage("");
      setError("");

      const data = await fetchJson(
        `/api/receivables/promise/${invoiceId}`,
        {
          method: "POST",
        }
      );

      setMessage(
        data.message ||
          `Promise recorded for ${invoiceId}`
      );

      await refreshAllData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  /*
   * Reset demo data.
   */
  async function handleResetDemo() {
    const confirmed = window.confirm(
      "Reset the demo data? This will clear recovery updates and audit records."
    );

    if (!confirmed) {
      return;
    }

    try {
      setLoading(true);
      setMessage("");
      setError("");

      const result = await fetchJson(
        "/api/demo/reset",
        {
          method: "POST",
        }
      );

      if (!result.success) {
        throw new Error(
          result.error ||
            "Failed to reset demo data"
        );
      }

      await refreshAllData();

      setMessage(
        "Demo data reset successfully."
      );
    } catch (requestError) {
      console.error(
        "Reset demo error:",
        requestError
      );

      setError(
        requestError.message ||
          "Unable to reset demo data"
      );
    } finally {
      setLoading(false);
    }
  }

  /*
   * Create a Razorpay recovery payment link.
   */
  async function handleRecoverPayment(payment) {
    const paymentId = payment.payment_id;

    try {
      setLoading(true);
      setMessage("");
      setError("");

      const data = await fetchJson(
        `/api/payments/${paymentId}/recover`,
        {
          method: "POST",
        }
      );

      const paymentLink =
        data.payment_link ||
        data.short_url ||
        data.url ||
        payment.payment_link;

      const paymentLinkId =
        data.payment_link_id ||
        data.id ||
        payment.payment_link_id;

      if (!paymentLink) {
        throw new Error(
          "Payment link was not returned by the backend."
        );
      }

      /*
       * Open the Razorpay checkout/payment page.
       */
      window.open(
        paymentLink,
        "_blank",
        "noopener,noreferrer"
      );

      setMessage(
        "Payment link opened. Waiting for payment confirmation..."
      );

      /*
       * Start automatic polling when the backend
       * returns a payment-link ID.
       */
      if (paymentLinkId) {
        setPollingPayment({
          paymentId,
          paymentLinkId,
        });
      } else {
        setMessage(
          "Payment link opened, but automatic status checking is unavailable."
        );
      }

      /*
       * Refresh immediately to show the newly created
       * payment link or updated recovery record.
       */
      await refreshAllData();
    } catch (requestError) {
      console.error(
        "Payment recovery failed:",
        requestError
      );

      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  /*
   * Determine whether a payment is recovered.
   */
  function isRecovered(payment) {
    const status = String(
      payment.recovery_status ||
        payment.status ||
        ""
    ).toLowerCase();

    return (
      status === "recovered" ||
      status === "paid" ||
      status === "captured" ||
      status === "successful" ||
    status === "success"
    );
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div>
          <h1>Revenue Recovery Dashboard</h1>

          <p>
            Monitor payments, receivables, recovery actions,
            and audit activity.
          </p>
        </div>

        <div className="header-actions">
          <button
            onClick={handleResetDemo}
            disabled={loading}
          >
            Reset Demo
          </button>

          <button
            className="refresh-button"
            onClick={refreshAllData}
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {message && (
        <div className="alert alert-success">
          {message}
        </div>
      )}

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <section className="summary-grid">
        <div className="summary-card">
          <span className="summary-label">
            Total at risk
          </span>

          <strong>
            {formatCurrency(summary.total_amount)}
          </strong>
        </div>

        <div className="summary-card">
          <span className="summary-label">
            Recovered amount
          </span>

          <strong className="text-success">
            {formatCurrency(summary.recovered_amount)}
          </strong>
        </div>

        <div className="summary-card">
          <span className="summary-label">
            Pending amount
          </span>

          <strong className="text-warning">
            {formatCurrency(summary.pending_amount)}
          </strong>
        </div>

        <div className="summary-card">
          <span className="summary-label">
            Recoverable amount
          </span>

          <strong>
            {formatCurrency(summary.recoverable_amount)}
          </strong>
        </div>

        <div className="summary-card">
          <span className="summary-label">
            Recovery rate
          </span>

          <strong>
            {Number(summary.recovery_rate || 0).toFixed(2)}%
          </strong>
        </div>

        <div className="summary-card">
          <span className="summary-label">
            Audit records
          </span>

          <strong>
            {summary.total_audit_records ||
              auditRecords.length}
          </strong>
        </div>
      </section>

      <nav className="tabs">
        <button
          className={
            activeTab === "recovery"
              ? "tab active-tab"
              : "tab"
          }
          onClick={() => setActiveTab("recovery")}
        >
          Payment Recovery
        </button>

        <button
          className={
            activeTab === "receivables"
              ? "tab active-tab"
              : "tab"
          }
          onClick={() => setActiveTab("receivables")}
        >
          Receivables
        </button>

        <button
          className={
            activeTab === "audit"
              ? "tab active-tab"
              : "tab"
          }
          onClick={() => setActiveTab("audit")}
        >
          Audit Log
        </button>
      </nav>

      {activeTab === "recovery" && (
        <section className="table-section">
          <div className="section-heading">
            <div>
              <h2>Payment recovery</h2>

              <p>
                Track pending and recovered payments.
              </p>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Payment ID</th>
                  <th>Customer</th>
                  <th>Amount</th>
                  <th>Risk</th>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Operation</th>
                </tr>
              </thead>

              <tbody>
                {payments.length === 0 ? (
                  <tr>
                    <td colSpan="7">
                      No payment records found.
                    </td>
                  </tr>
                ) : (
                  payments.map((payment) => (
                    <tr
                      key={payment.payment_id}
                    >
                      <td>
                        {payment.payment_id}
                      </td>

                      <td>
                        {payment.customer_name ||
                          payment.customer ||
                          "-"}
                      </td>

                      <td>
                        {formatCurrency(
                          payment.recovery_amount ??
                            payment.amount
                        )}
                      </td>

                      <td>
                        <span className="risk-badge">
                          {formatLabel(
                            payment.risk_level ||
                              payment.risk
                          )}
                        </span>
                      </td>

                      <td>
                        {formatLabel(
                          payment.action
                        )}
                      </td>

                      <td>
                        <span
                          className={getStatusClass(
                            payment.recovery_status ||
                              payment.status
                          )}
                        >
                          {formatLabel(
                            payment.recovery_status ||
                              payment.status
                          )}
                        </span>
                      </td>

                      <td>
                        {!isRecovered(payment) && (
                          <button
                            className="small-button"
                            onClick={() =>
                              handleRecoverPayment(payment)
                            }
                            disabled={loading}
                          >
                            Recover
                          </button>
                        )}

                        {isRecovered(payment) && (
                          <span className="completed-label">
                            Completed
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === "receivables" && (
        <section className="table-section">
          <div className="section-heading">
            <div>
              <h2>Receivables</h2>

              <p>
                Execute recommended collection actions
                and record promises to pay.
              </p>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Invoice ID</th>
                  <th>Company</th>
                  <th>Amount</th>
                  <th>Risk</th>
                  <th>Recommended action</th>
                  <th>Status</th>
                  <th>Operation</th>
                </tr>
              </thead>

              <tbody>
                {receivables.length === 0 ? (
                  <tr>
                    <td colSpan="7">
                      No receivables found.
                    </td>
                  </tr>
                ) : (
                  receivables.map((receivable) => (
                    <tr
                      key={receivable.invoice_id}
                    >
                      <td>
                        {receivable.invoice_id}
                      </td>

                      <td>
                        {receivable.company || "-"}
                      </td>

                      <td>
                        {formatCurrency(
                          receivable.amount
                        )}
                      </td>

                      <td>
                        <span className="risk-badge">
                          {formatLabel(
                            receivable.risk_level
                          )}
                        </span>
                      </td>

                      <td>
                        {formatLabel(
                          receivable.recommended_action
                        )}
                      </td>

                      <td>
                        <span
                          className={getStatusClass(
                            receivable.status
                          )}
                        >
                          {formatLabel(
                            receivable.status
                          )}
                        </span>
                      </td>

                      <td>
                        <div className="action-buttons">
                          <button
                            className="small-button"
                            onClick={() =>
                              handleExecuteAction(
                                receivable.invoice_id
                              )
                            }
                            disabled={loading}
                          >
                            Execute
                          </button>

                          <button
                            className="small-button secondary-button"
                            onClick={() =>
                              handlePromiseToPay(
                                receivable.invoice_id
                              )
                            }
                            disabled={loading}
                          >
                            Promise
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === "audit" && (
        <section className="table-section">
          <div className="section-heading">
            <div>
              <h2>Audit log</h2>

              <p>
                Payment and receivables actions are shown
                together from both CSV files.
              </p>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Reference</th>
                  <th>Customer / Company</th>
                  <th>Amount</th>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Created at</th>
                </tr>
              </thead>

              <tbody>
                {auditRecords.length === 0 ? (
                  <tr>
                    <td colSpan="7">
                      No audit records found.
                    </td>
                  </tr>
                ) : (
                  auditRecords.map((record, index) => (
                    <tr
                      key={`${record.audit_type || record.event}-${record.payment_id || record.invoice_id}-${record.created_at}-${index}`}
                    >
                      <td>
                        <span className="type-badge">
                          {formatLabel(
                            record.audit_type ||
                              record.event
                          )}
                        </span>
                      </td>

                      <td>
                        {record.invoice_id ||
                          record.payment_id ||
                          "-"}
                      </td>

                      <td>
                        {record.company ||
                          record.customer_name ||
                          record.customer ||
                          "-"}
                      </td>

                      <td>
                        {formatCurrency(
                          record.amount
                        )}
                      </td>

                      <td>
                        {formatLabel(
                          record.executed_action ||
                            record.action ||
                            "-"
                        )}
                      </td>

                      <td>
                        <span
                          className={getStatusClass(
                            record.status
                          )}
                        >
                          {formatLabel(
                            record.status
                          )}
                        </span>
                      </td>

                      <td>
                        {record.created_at || "-"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export default App;