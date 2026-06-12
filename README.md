# ForensicChain

A distributed forensic evidence management system built on a microservices architecture. Provides cryptographically verifiable evidence ingestion, immutable chain-of-custody tracking, and legally admissible PDF report generation.

---

## Getting Started

**Prerequisites:** Docker and Docker Compose

**1. Generate the RSA key pair** (private key is not included in the repository):

```bash
openssl genrsa -out keys/private_key.pem 2048
openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem
```

**2. Configure environment variables:**

```bash
cp .env.example .env
```

Edit `.env` and set a strong `JWT_SECRET` before any shared or production use.

**3. Start the stack:**

```bash
docker compose up --build
```

The UI is available at `http://localhost:8080`. The following users are seeded automatically:

| Username | Password | Role |
|---|---|---|
| `investigator01` | `investigator01` | investigator |
| `analyst01` | `analyst01` | forensic_analyst |
| `reviewer01` | `reviewer01` | legal_reviewer |
| `admin01` | `admin01` | admin |

---

## Services

### Auth Service (`services/auth-service/`)

Handles JWT issuance, validation, and role-based access control.

**Stack:** FastAPI · SQLAlchemy async · asyncpg · python-jose · bcrypt

- Issues JWT tokens on login; validates them for the gateway's `auth_request` calls.
- RBAC rules (`rbac.py`) map roles to permitted method/path pairs. Authorization is evaluated per request before any upstream service is reached.
- Manages users, cases, and case assignments via admin endpoints.

**Roles:** `investigator` · `forensic_analyst` · `legal_reviewer` · `admin`

---

### Evidence Collector (`services/evidence-collector/`)

Accepts evidence file uploads and coordinates the hashing/signing/ledger pipeline.

**Stack:** FastAPI · SQLAlchemy · PostgreSQL · RabbitMQ · gRPC client

- Streams uploaded files to shared storage, then calls Hash & Sign via gRPC to compute and sign the SHA-256 hash.
- Appends proof records to Immutable Ledger via gRPC.
- Publishes evidence and verification domain events using an outbox pattern (separate `outbox-worker` process) for reliable delivery.

---

### Hash & Sign (`services/hash-sign/`)

gRPC service for cryptographic file integrity.

**Stack:** Python · gRPC · cryptography (RSA-2048)

- **`ComputeAndSignHash`** — computes SHA-256 and signs with RSA-2048 private key.
- **`RecomputeHash`** — recomputes hash for verification.
- **`VerifySignature`** — verifies a hash/signature pair against the public key.

---

### Immutable Ledger (`services/immutable-ledger/`)

Append-only ledger with cryptographic chaining.

**Stack:** FastAPI · gRPC · SQLAlchemy · PostgreSQL

- Each record's hash covers its content plus the previous record's hash, making retroactive tampering detectable.
- **`AppendProofRecord`** / **`AppendVerificationRecord`** — gRPC write methods.
- **`ValidateLedgerChain`** — recomputes and verifies the entire chain on demand.
- REST endpoint for Audit Reporter: `GET /ledger/artifacts/{artifactId}`.

---

### Chain of Custody (`services/chain-of-custody/`)

Consumes custody events from RabbitMQ and maintains a per-artifact tamper-evident event chain.

**Stack:** FastAPI · SQLAlchemy 2.0 async · asyncpg · aio-pika · PostgreSQL

- Each event hash covers all fields (event_id, event_type, artifact_id, case_id, actor_id, actor_role, timestamp, reason, ip_address, correlation_id, payload, previous_event_hash) via `SHA-256(json.dumps(sort_keys=True))`.
- Idempotent: duplicate `event_id` values are dropped before any DB write.
- Retry strategy: up to 3 retries via `x-retry-count` header, then dead-letter queue via DLX.

**Endpoint:** `GET /custody/{artifactId}/timeline` → ordered events + `chain_valid` flag

---

### Audit Reporter (`services/audit-reporter/`)

Generates cryptographically verifiable PDF forensic reports.

**Stack:** FastAPI · WeasyPrint · Jinja2 · httpx · SQLAlchemy · aio-pika

- Aggregates artifact metadata, ledger proof, and custody timeline via internal REST calls.
- Anchors report hashes in Immutable Ledger via best-effort gRPC `AppendProofRecord` calls.
- Renders a Jinja2 HTML template and converts to PDF with WeasyPrint.
- Computes and stores SHA-256 of the PDF for later verification.
- Publishes `ReportGenerated`, `ReportDownloaded`, and `ReportVerified` events.

**Endpoints:** `POST /reports/{artifactId}` · `GET /reports/by-artifact/{artifactId}` · `GET /reports/{reportId}` · `GET /reports/{reportId}/download` · `POST /reports/{reportId}/verify`

---

### API Gateway (`services/gateway/`)

Nginx reverse proxy — sole public application entry point on port 8080.

- Every protected API request passes through `auth_request` to auth-service; returns `401`/`403` on failure.
- Injects `X-User-Id`, `X-User-Role`, `X-Correlation-Id` headers; downstream services trust these and do not re-decode the JWT.
- `client_max_body_size 100M` for evidence file uploads.

> **Note:** The RabbitMQ Management UI (`http://localhost:15672`) is exposed for local development and monitoring only. It should be disabled before any shared or production deployment.

---

### Forensic UI (`forensic-ui/`)

React single-page application for all four roles.

**Stack:** React 18 · TypeScript · Vite · TailwindCSS · Axios

- Role-aware navigation: each role sees only the routes it is permitted to access.
- Features: evidence upload and listing, artifact verification, custody timeline, ledger chain view, PDF report generation and download, user and case management (admin).

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
├── auth-service/           # JWT auth, RBAC, user/case management
├── evidence-collector/     # Evidence ingestion, outbox-worker
├── hash-sign/              # gRPC cryptographic hashing and signing
├── immutable-ledger/       # gRPC append-only proof ledger
├── chain-of-custody/       # RabbitMQ consumer, per-artifact hash chain
├── audit-reporter/         # PDF report generation and verification
└── gateway/                # Nginx reverse proxy with auth_request

forensic-ui/                # React + TypeScript frontend

proto/                      # Protobuf definitions for gRPC services
keys/                       # RSA-2048 public key (private key gitignored)
docs/                       # Event schema, port reference, RabbitMQ topology, design decisions
scripts/                    # JWT token generation utilities
tests/                      # Smoke, e2e, and negative test suites (41/41 passed)

docker-compose.yml          # Full stack: 5 DBs, RabbitMQ, 8 services, gateway, UI
```

---

## RSA Key Setup

The RSA private key is intentionally excluded from the repository. Before running the system locally, generate the key pair with:

```bash
openssl genrsa -out keys/private_key.pem 2048
openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem
```

---

## Development Tokens

`scripts/generate_demo_tokens.py` is a development/debug utility that generates short-lived JWT tokens for all four roles. It is **not** a substitute for the normal login flow (`POST /api/auth/login`) — use it only when you need a valid token quickly for API testing without going through the auth service.

The script must use the same `JWT_SECRET` as the auth service:

```bash
JWT_SECRET=your-secret python scripts/generate_demo_tokens.py
```
