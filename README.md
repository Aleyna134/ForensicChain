# ForensicChain — API Gateway · Chain of Custody · Audit Reporter

This branch (`feature/custody-reporting-gateway`) contains the implementation of the
**API Gateway**, **Chain of Custody Service**, and **Audit Reporter Service**,
along with the shared Docker Compose skeleton, RabbitMQ topology, and JWT infrastructure.

---

## Architecture Overview

```
                   ┌──────────────────────────────────────────────────────────┐
                   │                  API Gateway  (Nginx :8080)               │
                   │       auth_request → /internal/auth/validate              │
                   │       X-User-Id · X-User-Role · X-Correlation-Id         │
                   └────┬──────────────┬──────────────┬───────────────┬───────┘
                        │              │              │               │
              /evidence │     /custody │     /reports │      /ledger  │
                        ▼              ▼              ▼               ▼
             ┌──────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
             │  Evidence    │  │  Chain of  │  │   Audit    │  │ Immutable  │
             │  Collector   │  │  Custody   │  │  Reporter  │  │   Ledger   │
             │   :8001      │  │   :8004    │  │   :8005    │  │   :8003    │
             └──────┬───────┘  └─────┬──────┘  └─────┬──────┘  └────────────┘
                    │                │ consume         │ REST clients
                    │ publish        │                 │ (evidence · ledger · custody)
                    ▼                │                 │
             ┌────────────────┐      │                 │
             │   RabbitMQ     │◄─────┘                 │
             │ forensicchain  │◄───────────────────────┘
             │    .events     │
             └────────────────┘
```

---

## Services Implemented

### API Gateway (`services/gateway/`)

Nginx-based reverse proxy that sits in front of all services.

- Every request passes through `auth_request /internal/auth/validate`, which calls
  the Evidence Collector's JWT validation endpoint. Returns `401` for missing/invalid
  tokens and `403` for insufficient role.
- After successful validation, `X-User-Id`, `X-User-Role`, and `X-Correlation-Id`
  headers are injected into all upstream requests — downstream services trust these
  headers and do not re-decode the JWT.
- `client_max_body_size 100M` for forensic evidence file uploads.

---

### Chain of Custody Service (`services/chain-of-custody/`)

Consumes custody events from RabbitMQ and maintains a tamper-evident hash chain
per artifact.

**Stack:** FastAPI · SQLAlchemy 2.0 async · asyncpg · aio-pika · PostgreSQL

- **Fully async:** `create_async_engine` + `AsyncSession` — no blocking DB calls
  inside the async RabbitMQ consumer.
- **Per-artifact hash chain:** Each event's hash covers all meaningful fields
  (event_id, event_type, actor_id, actor_role, timestamp, reason, ip_address,
  payload, previous_event_hash) via `SHA-256(json.dumps(sort_keys=True))`.
  Tampering any field breaks the chain.
- **Idempotency:** Duplicate `event_id` values are dropped before any DB write.
- **Retry strategy:** `x-retry-count` header — up to 3 retries, then
  `reject(requeue=False)` routes the message to the DLQ via DLX.

**Endpoint:** `GET /custody/{artifactId}/timeline` → ordered events + `chain_valid` flag

---

### Audit Reporter Service (`services/audit-reporter/`)

Generates cryptographically verifiable PDF forensic reports by aggregating data
from three upstream services.

**Stack:** FastAPI · WeasyPrint · Jinja2 · httpx · SQLAlchemy · aio-pika

- Pulls artifact metadata, ledger proof, and custody timeline via internal REST calls.
- Renders a Jinja2 HTML template and converts it to PDF with WeasyPrint.
- Computes SHA-256 of the PDF bytes and stores it in `report_db` for later verification.
- Publishes `ReportGenerated`, `ReportDownloaded`, and `ReportVerified` events to RabbitMQ.

**Endpoints:** `POST /reports/{artifactId}` · `GET /reports/{reportId}` ·
`GET /reports/{reportId}/download` · `POST /reports/{reportId}/verify`

---

## RabbitMQ Topology

```
Exchange : forensicchain.events  (topic, durable)
Queue    : custody.events.queue  (durable, x-dead-letter-exchange → forensicchain.dlx)
Binding  : forensicchain.#  →  custody.events.queue

DLX      : forensicchain.dlx    (direct, durable)
DLQ      : custody.events.dlq   (durable)
```

---

## Project Structure

```
services/
├── gateway/
│   ├── nginx.conf            # Upstream defs, auth_request, 4 location blocks
│   ├── auth_validate.conf    # Internal auth sub-request location
│   └── Dockerfile
├── chain-of-custody/
│   ├── main.py               # Async lifespan: DB init, RabbitMQ topology, consumer task
│   ├── consumer.py           # aio-pika consumer: idempotency, retry, DLQ
│   ├── chain/custody_chain.py  # build_event_content(), compute_event_hash()
│   ├── db/                   # create_async_engine, models, async repository
│   └── routers/custody.py    # GET /custody/{artifactId}/timeline
└── audit-reporter/
    ├── main.py               # Lifespan: DB init, RabbitMQ exchange
    ├── report_generator.py   # build_report(): fetch → render → PDF → SHA-256
    ├── clients/              # httpx REST clients (evidence, ledger, custody)
    ├── db/                   # Report model and repository
    ├── rabbitmq/publisher.py # publish_event()
    ├── routers/reports.py    # POST/GET /reports/...
    └── templates/report.html # Jinja2 + WeasyPrint PDF template

docker-compose.yml            # Full stack: 4 DBs, RabbitMQ, 5 services, gateway
.env.example
scripts/generate_demo_tokens.py  # 4-role JWT generator
keys/public_key.pem              # RSA-2048 public key (private key is gitignored)
```
