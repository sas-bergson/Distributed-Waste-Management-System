# Notification Worker: Functional Requirements

| | |
|---|---|
| **Student** | Ebode Ada Erika |
| **Course** | Distributed Systems & Cloud Computing |
| **System** | Distributed Waste Management System (DWMS), capstone in Distributed Systems & Cloud Computing |
| **Service** | Notification Worker (inbox / email / SMS / push) with web sign-up and live inbox |
| **Objective(s)** | 3: a cloud service that lets clients follow the status of waste collection requests without refreshing the page [confirm with the lecturer] |
| **Repository** | https://github.com/ebodeadaerika/Notification-worker |

## 1. Purpose and scope

The Notification Worker is one microservice of the DWMS. Other services of the platform (for example the SPF Request Service when a collection request is created or changes status) place a **notification request** in a queue. The worker picks it up and delivers it **asynchronously** through the right channel: the in-app inbox, email, SMS or push. A small web application lets clients **sign up and log in**, and **only registered clients can receive notifications**.

Why a separate worker: the services that raise events (reports, requests, status changes) stay fast, because they only enqueue a message. Delivery, retries and failures are handled by the worker, and several workers can run side by side when volume grows.

In scope: accounts, notification submission, queueing, delivery, retries, failure handling, status tracking, and a web dashboard.
Out of scope: see section 6.

**Assumption to confirm:** the integration with the other DWMS services (which service sends which events) is described here by example only. The worker accepts any message in the format of section 4, so it does not depend on how the other services are built.

## 2. Actors

| Actor | Description |
|---|---|
| **Visitor** | A person who is not signed in. Can only see the sign-up and log-in pages. |
| **Client** | A registered, signed-in user of the platform. Receives notifications about waste reports and collection requests, and can send notifications to other clients. |
| **Other DWMS service** | A service of the platform (for example the SPF Request Service) that enqueues notification requests. |
| **Worker** | The background service that takes messages from the queue and delivers them. |
| **Operator** | The developer who runs the worker and uses the command-line producer to test the system. |
| **External services** | The queue (Upstash Redis) and the email server (SMTP, e.g. Gmail). |

## 3. Functional requirements

Status: **Done** = implemented and working. **Simulated** = the channel logs the delivery instead of calling a real provider.

### 3.1 Account management

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-A1 | A visitor shall be able to sign up with a name (1 to 60 characters), a valid email address (up to 120 characters) and a password (8 to 200 characters). | Done | `users.py`, `app.py` |
| FR-A2 | The system shall refuse to create a second account with an email address that is already registered. | Done | `users.py` |
| FR-A3 | The system shall store passwords only as salted hashes (PBKDF2-SHA256), never as plain text. | Done | `users.py` |
| FR-A4 | A client shall be able to log in with email and password. On failure, the system shall show the same message whether the email or the password was wrong. | Done | `users.py`, `app.py` |
| FR-A5 | The system shall block log-in for an email address for 15 minutes after 5 consecutive failed attempts. | Done | `users.py` |
| FR-A6 | A client shall be able to log out, which ends the session. | Done | `app.py` |
| FR-A7 | The dashboard and the inbox data shall only be available to signed-in clients; visitors shall be redirected to the log-in page. | Done | `app.py` |

### 3.2 Notification submission

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-B1 | A signed-in client shall be able to send a notification to any registered client, giving a title (up to 100 characters) and a message (up to 1000 characters). | Done | `app.py` |
| FR-B2 | If the recipient has no account, the system shall refuse the request, tell the sender, and queue nothing. | Done | `app.py` |
| FR-B3 | The system shall confirm that a notification is queued immediately; delivery happens afterwards. | Done | `app.py` |
| FR-B4 | Every notification shall receive a unique identifier and the status "queued" when it enters the queue. | Done | `app.py`, `producer.py` |
| FR-B5 | The operator shall be able to submit test notifications from the command line (a demo set, a message that always fails, a message for an unregistered recipient, a malformed message) and look up a notification's status by its identifier. | Done | `producer.py` |

### 3.3 Delivery channels

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-C1 | **Inbox:** the worker shall store the notification in the recipient's in-app inbox, keeping the latest 50, newest first. | Done | `handlers/inbox_handler.py` |
| FR-C2 | **Email:** the worker shall send the notification by email through an SMTP server over an encrypted connection (STARTTLS) to the recipient's account address. The subject shall be a single line. | Done | `handlers/email_handler.py` |
| FR-C3 | **SMS:** the worker shall route SMS notifications to an SMS handler. | Simulated | `handlers/sms_handler.py` |
| FR-C4 | **Push:** the worker shall route push notifications to a push handler. | Simulated | `handlers/push_handler.py` |
| FR-C5 | The worker shall choose the channel handler from the message's `type` field (`inbox`, `email`, `sms`, `push`). | Done | `worker.py`, `handlers/__init__.py` |
| FR-C6 | Email shall work in two modes: "mock" (log only) and "smtp" (really send), chosen in the configuration. | Done | `handlers/email_handler.py`, `config.py` |

### 3.4 Recipient preferences

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-D1 | A client shall be able to switch "also send my notifications by email" on or off on the dashboard. The default is off. | Done | `app.py`, `users.py`, `templates/dashboard.html` |
| FR-D2 | When a client has email switched on, every notification sent to that client shall be delivered both to the inbox and by email. | Done | `app.py` |

### 3.5 Queue processing (worker)

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-E1 | The worker shall run continuously and take messages from the queue one at a time, oldest first. | Done | `worker.py` |
| FR-E2 | The worker shall validate every message: known type, required fields for that type, and a recipient account. | Done | `message.py`, `worker.py` |
| FR-E3 | The worker shall reject any message whose recipient is not a registered client, so that only signed-up clients can receive notifications. | Done | `worker.py` |
| FR-E4 | A malformed or rejected message shall not be retried. It shall be moved to the failed queue together with the reason. | Done | `worker.py` |
| FR-E5 | If a delivery fails, the worker shall retry up to 3 times, waiting longer after each failure (2 seconds, then 4 seconds). | Done | `worker.py` |
| FR-E6 | When all retries fail, the worker shall move the message to the failed (dead-letter) queue with the error, and set its status to "failed". | Done | `worker.py` |
| FR-E7 | More than one worker shall be able to run at the same time; each message is taken by exactly one worker. | By design (atomic queue pop) | `worker.py` |
| FR-E8 | When stopped (Ctrl+C), the worker shall finish the message it is handling before exiting. | Done | `worker.py` |
| FR-E9 | If the connection to the queue drops or times out, the worker shall log the problem and try again after 3 seconds instead of crashing. | Done | `worker.py` |

### 3.6 Status tracking and logging

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-F1 | The system shall record a status for each notification: queued, processing, retrying, sent or failed, with the number of attempts, the last error, and the time of the last update. | Done | `worker.py` |
| FR-F2 | The worker shall log each important event (sent, failed attempt, rejected, moved to the failed queue) to the console and to the file `worker.log`. | Done | `worker.py` |

### 3.7 Web dashboard

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-G1 | The dashboard shall show the client's name, email address, and inbox. | Done | `templates/dashboard.html` |
| FR-G2 | The inbox shall refresh by itself every 10 seconds while the page is visible, without a reload. | Done | `static/dashboard.js` |
| FR-G3 | Notification text shall be displayed as plain text so that it can never run as HTML or script. | Done | `templates/`, `static/dashboard.js` |
| FR-G4 | A client shall only be able to see their own inbox. | Done | `app.py` |

### 3.8 Security behaviour

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-H1 | Every request that changes data (sign up, log in, log out, send, change settings) shall carry a CSRF token, and requests without a valid token shall be refused. | Done | `app.py` |
| FR-H2 | The session cookie shall be HttpOnly and SameSite=Lax, and the session shall be reset at log-in and log-out. | Done | `app.py` |
| FR-H3 | Every response shall include security headers (content-security policy, no-sniff, frame denial). | Done | `app.py` |

### 3.9 Configuration

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-I1 | Settings (queue address and token, SMTP login, retry count, cookie secret) shall be read from a private `.env` file that is never committed to the repository. A `.env.example` template shall document them. | Done | `config.py`, `.env.example`, `.gitignore` |
| FR-I2 | The operator shall be able to check the email settings on their own with a test command. | Done | `send_test_email.py` |

## 4. Message format

Every message in the queue is a JSON object. `user` is the account that receives the notification.

| Type | Required fields |
|---|---|
| `inbox` | `user`, `title`, `body` |
| `email` | `user`, `subject`, `body` (`to` defaults to the user's account email) |
| `sms` | `user`, `to` (phone number), `body` |
| `push` | `user`, `to` (device token), `title`, `body` |

Optional: `id` (generated if missing), `from` (sender).

## 5. Main use cases

| # | Use case | Flow |
|---|---|---|
| UC1 | Register | Visitor submits name, email and password, the account is created, and the client lands on the dashboard. |
| UC2 | Log in | Client enters email and password and reaches the dashboard. After 5 failures the account is blocked for 15 minutes. |
| UC3 | Send a notification | Client fills in the recipient, title and message. The system checks that the recipient has an account, queues the message, and confirms. |
| UC4 | Receive in the inbox | The worker takes the message from the queue, stores it in the recipient's inbox, and the dashboard shows it within 10 seconds. |
| UC5 | Receive by email | The client has email switched on. The worker sends the same notification to the client's email address as well. |
| UC6 | Failed delivery | A delivery fails, the worker retries 3 times, then moves the message to the failed queue with the error. |
| UC7 | Unknown recipient | A message for an address with no account is rejected and moved to the failed queue. |
| UC8 | Collection request update (example) | A DWMS service enqueues a message when the status of a collection request changes. The worker delivers it to the client who made the request, who sees it in the dashboard without refreshing. |

## 6. Out of scope / not implemented

- Real SMS and push delivery (the handlers are simulated and can be replaced by Twilio and Firebase Cloud Messaging).
- Password reset, email verification, and administrator or sender-only roles.
- Read/unread marks, deleting notifications, and delivery receipts.
- Priority queues and scheduled notifications.
- Protection against losing a message if the worker crashes in the middle of delivering it.
- Production deployment (the web app runs locally with Flask's development server).

## 7. Verification

Automated tests in the `tests/` folder (pytest) check validation, delivery, retries and the failed queue, sign-up and log-in rules, account lock-out, the signed-in-only rule, private inboxes, HTML escaping, and the email behaviour.
