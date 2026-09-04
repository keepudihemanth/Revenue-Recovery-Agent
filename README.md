
# AI Revenue Recovery

An AI-powered revenue recovery agent that detects revenue at risk, determines the right intervention, and executes a bounded recovery workflow.

Built for the **Razorpay Buildathon — Track 3**.

---

## Overview

Revenue loss rarely happens in one clean step. A payment may fail, a customer may abandon checkout, a subscription may stop renewing, or an invoice may remain overdue.
AI Revenue Recovery connects revenue-risk detection with practical recovery actions. The system identifies unsuccessful or outstanding payment events, evaluates whether recovery is appropriate, generates a Razorpay recovery link when required, synchronizes the latest payment status, and updates the internal receivable and audit records.
The current implementation focuses on reliable payment recovery, reconciliation, status tracking, and traceability. The collected receivable and recovery data also provides a foundation for future AI-based recovery prioritization.
---

## Problem Statement
Businesses can lose revenue at different stages of the payment lifecycle:
- Payments may fail after a customer attempts checkout.
- Customers may abandon the checkout process.
- Subscription payments may not complete successfully.
- Invoices may remain unpaid after their due date.
- Internal payment records may not match the latest gateway status.
- Support teams may not know which payments require immediate attention.
- Manual follow-ups may be slow, inconsistent, and difficult to track.

AI Revenue Recovery provides a centralized workflow to identify these situations, select an appropriate recovery action, verify the outcome, and maintain a clear history of each event.
---
## Project Objectives

- Detect payments and receivables that may result in revenue loss.
- Identify failed, pending, abandoned, and overdue payment scenarios.
- Determine whether a receivable is eligible for recovery.
- Generate Razorpay payment links for eligible recovery cases.
- Synchronize payment status with Razorpay before confirming recovery.
- Update receivable records after successful or unsuccessful recovery attempts.
- Maintain an audit trail for payment and recovery events.
- Prevent duplicate or uncontrolled recovery actions.
- Provide a dashboard for monitoring payment and recovery status.
- Create a foundation for future AI-based recovery prioritization.
---
## Key Features

### Revenue-Risk Detection
The system identifies revenue-risk scenarios such as:

- Failed payments
- Pending payments
- Checkout abandonment
- Subscription payment failures
- Overdue receivables
- Unreconciled payment records

### Recovery Link Generation
For eligible payments, the backend communicates with Razorpay to generate a recovery payment link.

### Payment Status Synchronization
The system checks the latest payment status from Razorpay instead of assuming that generating or opening a payment link means the payment was completed.

### Receivable Processing
Receivable records are evaluated using information such as:
- Outstanding amount
- Payment status
- Invoice status
- Due date
- Recovery eligibility
- Previous recovery attempts
- Final recovery outcome

### Audit Tracking
Important events are recorded so that the recovery process remains traceable and easier to debug.

### Dashboard Monitoring
The React frontend displays payment records, recovery status, and the latest synchronized results.
---

## System Architecture

```
React Frontend
      |
      | HTTP API Requests
      v
Flask Backend
      |
      +----------------------+
      |                      |
      v                      v
Receivables Engine     Recovery Engine
      |                      |
      |                      v
      |              Razorpay Service
      |                      |
      |                      v
      |                Razorpay API
      |
      v
Receivable Audit
      |
      v
Updated Payment and Recovery Status
````

The frontend is responsible for displaying information and initiating user actions. The Flask backend contains the business logic, communicates with Razorpay, validates requests, updates receivables, and records recovery events.

## Project Structure

```
AI-Revenue-Recovery/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── ...
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   │
│   ├── services/
│   │   ├── razorpay_service.py
│   │   ├── receivable_audit.py
│   │   ├── receivables_engine.py
│   │   └── recovery_engine.py
│   │
│   ├── data/
│   │   └── ...
│
└── README.md
```

## Backend File Responsibilities

### `app.py`
The main entry point of the Flask application.
Responsibilities:
* Creates the Flask application.
* Enables CORS.
* Registers API routes.
* Loads configuration.
* Starts the backend server.

### `requirements.txt`
Contains the Python dependencies required to run the backend, such as:
* Flask
* Flask-CORS
* Razorpay SDK
* Python-dotenv
* Database libraries
* Other supporting packages

### `razorpay_service.py`
Handles communication with Razorpay.
Responsibilities:
* Initialize the Razorpay client.
* Create payment or recovery links.
* Fetch payment details.
* Fetch payment-link details.
* Retrieve the latest payment status.
* Handle Razorpay API errors.
This file keeps gateway-specific logic separate from the rest of the application and prevents the frontend from directly accessing Razorpay credentials.

### `receivable_audit.py`

Maintains the history of receivable and recovery events.
It can record events such as:
* Payment created
* Payment failed
* Payment marked as pending
* Recovery link generated
* Payment status synchronized
* Payment recovered
* Recovery attempt failed

This provides traceability for debugging, reconciliation, and customer-support activities.

### `receivables_engine.py`
Processes receivable records and identifies outstanding revenue.
Responsibilities:
* Read receivable information.
* Check payment and invoice status.
* Calculate outstanding amounts.
* Identify overdue or pending receivables.
* Determine which records require recovery.
* Update receivable information.

This engine provides the data-processing layer for the recovery workflow.

### `recovery_engine.py`

Coordinates the recovery process.
Responsibilities:
* Check recovery eligibility.
* Prevent duplicate recovery attempts.
* Request a recovery link through `razorpay_service.py`.
* Track recovery-link details.
* Synchronize the payment status after customer payment.
* Update the receivable status.
* Record the recovery result in the audit history.

### `data/`

Contains input and supporting data used by the application.
During development, this folder contains synthetic payment and receivable records used to test different revenue-risk scenarios without exposing real customer information.

## Synthetic Dataset

Because real payment and receivable data was not available for every scenario, a synthetic dataset was created for development and testing.
The dataset represents different payment situations, including:
* Successful payments
* Failed payments
* Pending payments
* Abandoned checkouts
* Subscription failures
* Overdue invoices
* High-value receivables
* Receivables with previous recovery attempts

### Example Synthetic Record
JSON
```
{
  "payment_id": "pay_005",
  "customer_id": "cust_005",
  "amount": 2500,
  "currency": "INR",
  "payment_status": "failed",
  "receivable_status": "outstanding",
  "due_date": "2026-08-30",
  "recovery_attempts": 0
}
```

### Why Synthetic Data Was Used

* It avoids exposing real customer or payment information.
* It allows controlled testing of different failure scenarios.
* It helps verify recovery and reconciliation logic.
* It makes demonstrations repeatable.
* It provides a foundation for future AI model training and evaluation.

The synthetic dataset is intended for development and demonstration purposes. It does not represent actual customer transactions.

## Technology Stack

### Frontend

* React
* Vite
* JavaScript
* CSS
### Backend

* Python
* Flask
* Flask-CORS
* REST APIs
  
### Payment Gateway

* Razorpay Test API
  
### Data Processing

* Synthetic payment and receivable dataset
* JSON or database-backed records
* Python-based processing and validation

### Development Tools

* Git
* GitHub
* Visual Studio Code
* Postman or browser-based API testing

## Installation

### Prerequisites

Install the following before running the project:

* Python 3.9 or later
* Node.js and npm
* Git
* A Razorpay test account
* Razorpay test API credentials

## Clone the Repository

Bash

```
git clone <your-repository-url>
cd <your-project-folder>
```

## Backend Setup

Navigate to the backend directory:

Bash

```
cd backend
```

Create a virtual environment:

Bash

```
python -m venv venv
```

Activate the virtual environment.

### Windows

Bash

```
venv\Scripts\activate
```

### macOS or Linux

Bash

```
source venv/bin/activate
```

Install the dependencies:

Bash

```
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file inside the backend directory.

env

```
RAZORPAY_KEY_ID=your_razorpay_test_key_id
RAZORPAY_KEY_SECRET=your_razorpay_test_key_secret
```

Use only Razorpay test credentials during development.

Do not commit the `.env` file or expose the secret key in the frontend, screenshots, README files, or GitHub repository.

Add the following to `.gitignore` if it is not already present:

gitignore

```
.env
venv/
__pycache__/
*.pyc
```

## Run the Backend

From the `backend` directory:

Bash

```
python app.py
```

The backend will normally run at:

```
http://127.0.0.1:5000
```

## Frontend Setup

Open a new terminal and navigate to the frontend directory:

Bash

```
cd frontend
```

Install the frontend dependencies:

Bash

```
npm install
```

Start the development server:

Bash

```
npm run dev
```

The frontend will normally be available at:

```
http://localhost:5173
```

The frontend communicates with the Flask backend using the configured API base URL.

## Razorpay Test Mode

This project uses Razorpay Test Mode for development.

Test Mode allows the recovery workflow to be demonstrated without processing real money.

### Setup Process

1. Create or access a Razorpay test account.
2. Open the API key section in the Razorpay dashboard.
3. Generate test API credentials.
4. Add the test credentials to the backend `.env` file.
5. Start the Flask backend.
6. Start the React frontend.
7. Use the dashboard to create or recover test payment records.
8. Verify the payment status through the backend synchronization process.

Never use production credentials while testing the application.

## Usage Workflow

### 1. View Revenue at Risk
Open the dashboard to view payment and receivable records.
The system displays records that may require attention, including failed, pending, abandoned, or overdue payments.

### 2. Select a Payment
Choose a payment or receivable that is eligible for recovery.

### 3. Start Recovery
The frontend sends a recovery request to the Flask backend.

The backend:

1. Validates the payment information.
2. Checks the receivable status.
3. Verifies recovery eligibility.
4. Calls the recovery engine.
5. Uses the Razorpay service to generate a payment link.

### 4. Complete the Payment

Open the generated Razorpay test payment link and complete the test payment flow.

### 5. Synchronize the Status

The backend checks the latest payment status from Razorpay.
The system does not mark a payment as recovered only because a recovery link was created. Recovery is confirmed after the payment status is synchronized and verified.

### 6. Update the Dashboard

After successful synchronization:
* The payment status is updated.
* The receivable status is updated.
* The recovery result is recorded.
* The audit history is updated.
* The frontend displays the latest status.

## Example Recovery Flow

```
Failed Payment
      ↓
Receivable Identified
      ↓
Recovery Eligibility Checked
      ↓
Razorpay Test Payment Link Created
      ↓
Customer Completes Payment
      ↓
Payment Status Synchronized
      ↓
Receivable Marked as Recovered
      ↓
Audit Event Recorded
```

## API Workflow

The frontend communicates with the backend through REST endpoints.

Typical operations include:

```
GET  /api/health
POST /api/payments/<payment_id>/recover
POST /api/payment-links/<payment_link_id>/sync
```

The exact available endpoints depend on the backend route implementation.

### Recovery Request

http

```
POST /api/payments/pay_005/recover
```

The backend returns a recovery-link response when the payment is eligible for recovery.

### Status Synchronization

http

```
POST /api/payment-links/<payment_link_id>/sync
```

The synchronization response contains the latest payment and recovery information.

Example response:

JSON

```
{
  "success": true,
  "razorpay_status": "paid",
  "audit_status": "recovered",
  "payment": {
    "payment_id": "pay_005",
    "status": "recovered",
    "recovery_status": "recovered"
  }
}
```


## Handling Failures

During development, several technical issues had to be handled.
### Frontend–Backend Communication
The React frontend and Flask backend run on different ports during development. CORS configuration and a consistent API base URL were used to allow communication between them.

### Razorpay API Errors
Invalid payment IDs, missing credentials, and failed API requests can cause errors. These cases are handled through validation and structured error responses.

### Inconsistent Payment Statuses
Different responses may use fields such as:

* `status`
* `recovery_status`
* `razorpay_status`
* `audit_status`

The backend and frontend normalize these values before displaying the final recovery state.

### Pending Payments

A pending payment is not immediately treated as recovered. The system continues to synchronize the payment status before updating the receivable.

### Synthetic Data Validation

The synthetic dataset was used to test multiple scenarios and confirm that failed, pending, overdue, and recovered records were processed correctly.

## Current Scope

The current version provides:

* Revenue-risk record display
* Synthetic payment and receivable data
* Razorpay test-mode integration
* Recovery-link generation
* Payment-status synchronization
* Receivable status updates
* Recovery audit tracking
* React dashboard

The current implementation does not automatically perform unrestricted financial actions or use production payment credentials.

## Future Enhancements

Future versions can include:

* AI-based recovery probability prediction
* Recovery prioritization based on amount, age, and customer history
* Automatic intervention selection
* Personalized recovery messages
* Subscription-specific recovery workflows
* Email and SMS notifications
* Advanced revenue analytics
* Database-backed audit history
* Role-based access control
* Human approval for high-value recovery actions
* Model monitoring and recovery-performance evaluation

## Project Value

AI Revenue Recovery connects revenue-risk detection, intervention selection, payment execution, and reconciliation in one workflow.
Instead of treating failed payments and overdue receivables as isolated records, the system provides a structured process to identify the issue, initiate an appropriate recovery action, verify the result, and preserve a clear history of the outcome.
This improves operational visibility, reduces manual follow-up, and creates a foundation for intelligent revenue recovery.

##NOTE 
Thank you for time and Consideration

## License

This project was developed for the Razorpay Buildathon and is intended for educational, demonstration, and development purposes.
