# ForensicChain — Implementation Plan

**CENG-442 Microservice Architecture · Submission 2**  
**Team:** Aleyna Karaağaç (22118080088) · Irmak Su Yıldız (23118080013)  
**Last updated:** May 2026

---

## Table of Contents

1. [Work Division](#1-work-division)
2. [First Session Checklist](#2-first-session-checklist)
3. [Finalized Technical Decisions](#3-finalized-technical-decisions)
4. [Repository Structure](#4-repository-structure)
5. [Docker Compose & Infrastructure](#5-docker-compose--infrastructure)
6. [gRPC Contracts (.proto files)](#6-grpc-contracts-proto-files)
7. [RabbitMQ Topology](#7-rabbitmq-topology)
8. [Event Schema](#8-event-schema)
9. [REST API Contracts](#9-rest-api-contracts)
10. [Database Schemas](#10-database-schemas)
11. [JWT & Authentication Strategy](#11-jwt--authentication-strategy)
12. [Service-by-Service Implementation Guide](#12-service-by-service-implementation-guide)
13. [Error Handling Decisions](#13-error-handling-decisions)
14. [Integration Order & Milestones](#14-integration-order--milestones)
15. [Demo Scenario](#15-demo-scenario)

---

## 1. Work Division

| Area | Person A | Person B |
|---|---|---|
| **Services** | Evidence Collector · Hash & Sign · Immutable Ledger | API Gateway (Nginx) · Chain of Custody · Audit Reporter |
| **Infrastructure** | Shared Docker volume · evidence_db · ledger_db | RabbitMQ setup · custody_db · report_db · Docker Compose skeleton |
| **Contracts** | `proto/hash_sign.proto` · `proto/ledger.proto` | `docs/event-schema.md` · `docs/rabbitmq-topology.md` |
| **Core flow** | Upload → hash → sign → ledger → publish event | Consume event → custody chain → report generation → report hash |

**Dependency between the two sides:**  
Person A publishes `EvidenceIngested` to RabbitMQ after successful ingestion.  
Person B's Chain of Custody Service consumes it.  
The only coupling is the **event envelope format** — defined once in Section 8, never changed unilaterally.

---

## 2. First Session Checklist

Complete these together before writing any service code.

```
[ ] Create GitHub repository
[ ] Create branch structure: main / dev / feature/ingestion-integrity / feature/custody-reporting-gateway
[ ] Copy docker-compose.yml skeleton from Section 5
[ ] Copy both .proto files from Section 6
[ ] Copy .env.example from Section 5
[ ] Run: docker compose up rabbitmq evidence-db ledger-db custody-db report-db
[ ] Verify all containers are healthy
[ ] Create empty FastAPI app in each service directory with GET /health endpoint
[ ] Run: docker compose up --build
[ ] Verify all /health endpoints return 200
[ ] Generate demo JWT tokens using scripts/generate_demo_tokens.py (Section 11)
[ ] Write docs/implementation-decisions.md (copy from Section 3)
```

**Target of first session:** All containers up, all `/health` endpoints returning `{"status": "ok"}`, demo tokens generated.

---

## 3. Finalized Technical Decisions

These decisions are final. Do not change them unilaterally — discuss first, update this document together.

```
# docs/implementation-decisions.md

1. FILE TRANSFER
   Evidence Collector saves uploaded binary to shared Docker volume at:
   /evidence-storage/{artifact_id}/original.bin
   Hash & Sign Service accesses the file via shared volume (read-only mount).
   No binary bytes transferred over gRPC. No streaming in MVP.

2. GRPC CONTRACTS
   Two proto files: proto/hash_sign.proto and proto/ledger.proto
   ArtifactHashRequest uses file_path (string), not bytes content.
   Timestamp fields use string (ISO 8601) in MVP for simplicity.

3. RABBITMQ
   Exchange name : forensicchain.events
   Exchange type : topic
   Durable       : true
   Main queue    : custody.events.queue
   Binding       : forensicchain.#  (catches all routing keys)
   DLX exchange  : forensicchain.dlx
   DLQ queue     : custody.events.dlq
   Routing key format: forensicchain.<domain>.<action>
   Retry strategy: consumer tracks x-retry-count header.
                   On failure: if retry_count < 3, publish a retry copy with
                   x-retry-count+1 to forensicchain.events (same routing key),
                   then ack the original message. The retry copy becomes the live message.
                   After retry_count reaches 3, reject the message with requeue=False
                   so RabbitMQ routes it to the DLQ via forensicchain.dlx.
                   Total attempts = 1 initial + 3 retries = 4 attempts before DLQ.
                   To reduce to 3 total attempts, change the condition to retry_count < 2.
                   No x-message-ttl on the queue (TTL is not a retry mechanism).

4. EVENT ENVELOPE
   All events share the same JSON envelope (see Section 8).
   event_id, artifact_id, correlation_id: UUID v4.
   Timestamp: ISO 8601 UTC string.
   OUTBOX PAYLOAD RULE: outbox_events.payload stores the FULL event envelope,
   not only the inner event-specific payload field. The RabbitMQ message body
   must always contain event_id, event_type, routing_key, artifact_id,
   actor_id, actor_role, timestamp, correlation_id, reason, and payload.
   Chain of Custody consumer reads these top-level fields directly.

5. ID FORMAT
   artifact_id  : UUID v4 (plain, no prefix in DB)
   event_id     : UUID v4
   report_id    : UUID v4
   correlation_id: UUID v4
   ledger_record_id: UUID v4

6. JWT
   Algorithm  : HS256
   Secret     : loaded from JWT_SECRET env var (set in .env)
   Expiry     : 30 days for demo tokens
   Tokens generated once with scripts/generate_demo_tokens.py
   Nginx routes all external traffic.
   JWT validation is performed through Nginx auth_request by calling
   /internal/auth/validate on the Evidence Collector Service.
   Downstream services trust X-User-Id, X-User-Role, and X-Correlation-Id
   headers forwarded by the gateway — they do not re-decode the JWT.
   Shared FastAPI JWT middleware is used only for local development or
   direct service debugging (bypassing the gateway).

7. INGESTION FAILURE HANDLING
   If Hash & Sign fails   → reject ingestion, return 503, no ledger record, no event.
   If Ledger append fails → reject ingestion, return 503, no event published.
   If RabbitMQ publish fails → ingestion is confirmed (hash+ledger succeeded).
                               Event stored in outbox table, retried by background worker.

8. DUPLICATE ARTIFACT
   Same file uploaded twice → allowed. New artifact_id generated each time.
   No deduplication in MVP.

9. VERIFICATION FLOW
   POST /evidence/{artifactId}/verify accepts a file upload (the file to check).
   Evidence Collector saves it to the shared volume at:
   /evidence-storage/tmp/{artifact_id}/{verification_id}.bin
   (NOT to local /tmp — Hash & Sign must be able to read this path via shared volume.)

   Full verification steps:
   1. Save uploaded file to /evidence-storage/tmp/{artifact_id}/{verification_id}.bin
   2. Call Hash & Sign → RecomputeHash(temp_file_path) → current_hash
   3. Call Ledger     → GetProofByArtifactId(artifact_id) → original_hash + signature_value
   4. Call Hash & Sign → VerifySignature(original_hash, signature_value) → signature_valid
   5. Call Ledger     → ValidateLedgerChain() → ledger_chain_valid
   6. Compare original_hash == current_hash → VALID or TAMPERED
   7. Append VerificationRecord to Ledger (verification_result, original_hash, current_hash)
   8. Publish VerificationPassed or VerificationFailed event to RabbitMQ
   9. Delete temp file from /evidence-storage/tmp/

   Response includes: verification_result, original_hash, current_hash,
                      signature_valid, ledger_chain_valid.

10. REPORT TRIGGER
    POST /reports/{artifactId} triggers report generation.
    Audit Reporter pulls from Evidence Collector, Ledger, Chain of Custody via REST.
    Computes SHA-256 of the generated PDF/HTML bytes.
    Stores report metadata + hash in report_db.
    Publishes ReportGenerated event.
    ReportDownloaded is published when GET /reports/{reportId}/download is called.
    ReportVerified is published when POST /reports/{reportId}/verify is called.

11. AUDIT REPORTER → LEDGER COMMUNICATION
    Audit Reporter calls Ledger via REST (GET /ledger/artifacts/{artifactId}).
    No gRPC needed between Audit Reporter and Ledger.

12. DEMO PRE-FLIGHT (Port Lockdown)
    Development: all service ports are open to host for debugging.
    Before demo: in docker-compose.yml, comment out "ports:" on all internal
    services and switch to "expose:" only. See Milestone 6 for exact checklist.
    Only gateway:8080 and rabbitmq:15672 (management UI) remain host-accessible.
    RabbitMQ AMQP port 5672 must also be closed to host before demo — internal
    services reach it via rabbitmq:5672 on the Docker network without host exposure.

13. CROSS-SERVICE HEADERS
    All internal REST calls include:
    X-Correlation-Id : forwarded from original request
    X-User-Id        : forwarded from gateway
    X-User-Role      : forwarded from gateway
```

---

## 4. Repository Structure

```
forensicchain/
├── docker-compose.yml
├── .env.example
├── .env                          ← gitignored
│
├── proto/
│   ├── hash_sign.proto
│   └── ledger.proto
│
├── docs/
│   ├── implementation-decisions.md
│   ├── event-schema.md
│   ├── rabbitmq-topology.md
│   └── service-ports.md
│
├── scripts/
│   └── generate_demo_tokens.py
│
├── services/
│   ├── evidence-collector/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models/
│   │   ├── db/
│   │   ├── grpc_clients/
│   │   ├── rabbitmq/
│   │   │   └── outbox_publisher.py
│   │   └── auth/
│   │       └── middleware.py     ← shared auth logic
│   │
│   ├── hash-sign/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py               ← gRPC server
│   │   ├── servicer.py
│   │   └── crypto/
│   │       ├── hasher.py
│   │       └── signer.py
│   │
│   ├── immutable-ledger/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py               ← gRPC + REST server
│   │   ├── servicer.py
│   │   ├── chain/
│   │   │   └── hash_chain.py
│   │   └── db/
│   │
│   ├── chain-of-custody/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── consumer.py           ← RabbitMQ consumer
│   │   ├── chain/
│   │   │   └── custody_chain.py
│   │   └── db/
│   │
│   ├── audit-reporter/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── report_generator.py
│   │   ├── clients/              ← REST clients for other services
│   │   └── db/
│   │
│   └── gateway/
│       ├── nginx.conf
│       ├── auth_validate.conf
│       └── Dockerfile
│
└── keys/
    ├── private_key.pem           ← gitignored
    └── public_key.pem
```

---

## 5. Docker Compose & Infrastructure

### .env.example

```env
# JWT
JWT_SECRET=dev-secret-key-change-in-production

# PostgreSQL
POSTGRES_USER=forensic
POSTGRES_PASSWORD=forensic_pass

EVIDENCE_DB_URL=postgresql://forensic:forensic_pass@evidence-db:5432/evidence_db
LEDGER_DB_URL=postgresql://forensic:forensic_pass@ledger-db:5432/ledger_db
CUSTODY_DB_URL=postgresql://forensic:forensic_pass@custody-db:5432/custody_db
REPORT_DB_URL=postgresql://forensic:forensic_pass@report-db:5432/report_db

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
RABBITMQ_EXCHANGE=forensicchain.events
RABBITMQ_QUEUE=custody.events.queue

# gRPC
HASH_SIGN_GRPC_HOST=hash-sign-service
HASH_SIGN_GRPC_PORT=50051
LEDGER_GRPC_HOST=ledger-service
LEDGER_GRPC_PORT=50052

# Internal service URLs (for REST calls)
EVIDENCE_SERVICE_URL=http://evidence-service:8001
LEDGER_SERVICE_URL=http://ledger-service:8003
CUSTODY_SERVICE_URL=http://custody-service:8004

# Storage
EVIDENCE_STORAGE_PATH=/evidence-storage
REPORT_STORAGE_PATH=/report-storage
```

### docker-compose.yml

```yaml
version: "3.9"

volumes:
  evidence_storage:
  evidence_db_data:
  ledger_db_data:
  custody_db_data:
  report_db_data:
  report_storage:

networks:
  forensicchain_net:
    driver: bridge

services:

  # ── Databases ──────────────────────────────────────────────────────

  evidence-db:
    image: postgres:16-alpine
    container_name: evidence-db
    environment:
      POSTGRES_DB: evidence_db
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - evidence_db_data:/var/lib/postgresql/data
    # Development: host port open for direct DB access (psql, DBeaver etc.).
    # BEFORE DEMO: comment out "ports:" — services reach evidence-db:5432 via Docker network.
    ports:
      - "5433:5432"
    networks: [forensicchain_net]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d evidence_db"]
      interval: 5s
      retries: 5

  ledger-db:
    image: postgres:16-alpine
    container_name: ledger-db
    environment:
      POSTGRES_DB: ledger_db
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ledger_db_data:/var/lib/postgresql/data
    # BEFORE DEMO: comment out "ports:".
    ports:
      - "5434:5432"
    networks: [forensicchain_net]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ledger_db"]
      interval: 5s
      retries: 5

  custody-db:
    image: postgres:16-alpine
    container_name: custody-db
    environment:
      POSTGRES_DB: custody_db
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - custody_db_data:/var/lib/postgresql/data
    # BEFORE DEMO: comment out "ports:".
    ports:
      - "5435:5432"
    networks: [forensicchain_net]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d custody_db"]
      interval: 5s
      retries: 5

  report-db:
    image: postgres:16-alpine
    container_name: report-db
    environment:
      POSTGRES_DB: report_db
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - report_db_data:/var/lib/postgresql/data
    # BEFORE DEMO: comment out "ports:".
    ports:
      - "5436:5432"
    networks: [forensicchain_net]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d report_db"]
      interval: 5s
      retries: 5

  # ── Message Broker ─────────────────────────────────────────────────

  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    container_name: rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    # Development: both AMQP and management UI open to host.
    # BEFORE DEMO: close 5672 — internal services reach rabbitmq:5672 via Docker
    # network without host exposure. Keep 15672 only if you want the UI during demo.
    ports:
      - "5672:5672"
      - "15672:15672"    # management UI
    # expose:            # ← use this instead of "ports:" before demo
    #   - "5672"
    # and re-add "15672:15672" only if management UI is needed during demo
    networks: [forensicchain_net]
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      retries: 5

  # ── Services ────────────────────────────────────────────────────────

  evidence-service:
    build: ./services/evidence-collector
    container_name: evidence-service
    env_file: .env
    volumes:
      - evidence_storage:/evidence-storage
    # Development: host port open for direct debugging.
    # BEFORE DEMO: comment out "ports:" and uncomment "expose:" so all
    # external traffic is forced through the API Gateway (port 8080 only).
    ports:
      - "8001:8001"
    # expose:
    #   - "8001"
    networks: [forensicchain_net]
    depends_on:
      evidence-db:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      hash-sign-service:
        condition: service_started
      ledger-service:
        condition: service_started

  hash-sign-service:
    build: ./services/hash-sign
    container_name: hash-sign-service
    env_file: .env
    volumes:
      - evidence_storage:/evidence-storage:ro
      - ./keys:/keys:ro
    # BEFORE DEMO: comment out "ports:", uncomment "expose:".
    ports:
      - "50051:50051"
    # expose:
    #   - "50051"
    networks: [forensicchain_net]

  ledger-service:
    build: ./services/immutable-ledger
    container_name: ledger-service
    env_file: .env
    # BEFORE DEMO: comment out "ports:", uncomment "expose:".
    ports:
      - "50052:50052"
      - "8003:8003"
    # expose:
    #   - "50052"
    #   - "8003"
    networks: [forensicchain_net]
    depends_on:
      ledger-db:
        condition: service_healthy

  custody-service:
    build: ./services/chain-of-custody
    container_name: custody-service
    env_file: .env
    # BEFORE DEMO: comment out "ports:", uncomment "expose:".
    ports:
      - "8004:8004"
    # expose:
    #   - "8004"
    networks: [forensicchain_net]
    depends_on:
      custody-db:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  report-service:
    build: ./services/audit-reporter
    container_name: report-service
    env_file: .env
    volumes:
      - report_storage:/report-storage
    # BEFORE DEMO: comment out "ports:", uncomment "expose:".
    ports:
      - "8005:8005"
    # expose:
    #   - "8005"
    networks: [forensicchain_net]
    depends_on:
      report-db:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  gateway:
    build: ./services/gateway
    container_name: api-gateway
    ports:
      - "8080:8080"
    networks: [forensicchain_net]
    depends_on:
      - evidence-service
      - custody-service
      - report-service
      - ledger-service
```

### Service Ports Reference

| Container | Internal Port | Host Port (dev) | Host Port (demo) | Protocol |
|---|---|---|---|---|
| api-gateway | 8080 | 8080 | 8080 | HTTP |
| evidence-service | 8001 | 8001 | **closed** (expose only) | HTTP/REST |
| hash-sign-service | 50051 | 50051 | **closed** (expose only) | gRPC |
| ledger-service | 50052 + 8003 | 50052 + 8003 | **closed** (expose only) | gRPC + REST |
| custody-service | 8004 | 8004 | **closed** (expose only) | HTTP/REST |
| report-service | 8005 | 8005 | **closed** (expose only) | HTTP/REST |
| rabbitmq | 5672 + 15672 | 5672 + 15672 | **5672 closed**, 15672 optional | AMQP + UI |
| evidence-db | 5432 | 5433 | **closed** | PostgreSQL |
| ledger-db | 5432 | 5434 | **closed** | PostgreSQL |
| custody-db | 5432 | 5435 | **closed** | PostgreSQL |
| report-db | 5432 | 5436 | **closed** | PostgreSQL |

> **Before demo:** Comment out `ports:` on all internal services and switch to `expose:` only. See Milestone 6 checklist.

---

## 6. gRPC Contracts (.proto files)

### proto/hash_sign.proto

```protobuf
syntax = "proto3";

package forensicchain.hashsign;

service HashSignService {
  rpc ComputeAndSignHash (ArtifactHashRequest)    returns (IntegrityProofResponse);
  rpc RecomputeHash      (ArtifactHashRequest)    returns (HashResponse);
  rpc VerifySignature    (SignatureVerifyRequest)  returns (SignatureVerifyResponse);
}

// Request: Evidence Collector → Hash & Sign
// File is read from shared volume using file_path.
// No binary bytes transferred.
message ArtifactHashRequest {
  string artifact_id     = 1;
  string case_id         = 2;
  string file_path       = 3;  // absolute path inside container, e.g. /evidence-storage/{artifact_id}/original.bin
  string file_name       = 4;
  int64  file_size       = 5;  // bytes
  string hash_algorithm  = 6;  // always "SHA-256" in MVP
}

// Response: hash + digital signature
message IntegrityProofResponse {
  string artifact_id        = 1;
  string case_id            = 2;
  string hash_algorithm     = 3;
  string hash_value         = 4;  // hex-encoded SHA-256
  string signature_algorithm = 5; // "RSA-SHA256"
  string signature_value    = 6;  // base64-encoded signature
  string signer_id          = 7;  // "hash-sign-service"
  string signed_at          = 8;  // ISO 8601 UTC
  bool   success            = 9;
  string error_message      = 10;
}

// Response: hash only (used during verification)
message HashResponse {
  string artifact_id     = 1;
  string hash_algorithm  = 2;
  string hash_value      = 3;
  bool   success         = 4;
  string error_message   = 5;
}

// Request: verify an existing signature
message SignatureVerifyRequest {
  string artifact_id        = 1;
  string hash_value         = 2;
  string signature_value    = 3;
  string signature_algorithm = 4;
}

// Response: signature validity
message SignatureVerifyResponse {
  string artifact_id    = 1;
  bool   signature_valid = 2;
  bool   success        = 3;
  string error_message  = 4;
}
```

### proto/ledger.proto

```protobuf
syntax = "proto3";

package forensicchain.ledger;

service LedgerService {
  rpc AppendProofRecord        (ProofRecordRequest)        returns (ProofRecordResponse);
  rpc AppendVerificationRecord (VerificationRecordRequest) returns (ProofRecordResponse);
  rpc GetProofByArtifactId     (ArtifactProofRequest)      returns (ArtifactIntegrityProofResponse);
  rpc ValidateLedgerChain      (ValidateLedgerRequest)     returns (ValidateLedgerResponse);
}

// Append a new integrity proof record (called after hash + sign)
message ProofRecordRequest {
  string artifact_id        = 1;
  string case_id            = 2;
  string record_type        = 3;  // "EVIDENCE_PROOF_CREATED"
  string hash_algorithm     = 4;
  string hash_value         = 5;
  string signature_algorithm = 6;
  string signature_value    = 7;
  string signer_id          = 8;
  string created_at         = 9;  // ISO 8601 UTC
}

// Append a verification result record
message VerificationRecordRequest {
  string artifact_id          = 1;
  string case_id              = 2;
  string record_type          = 3;  // "VERIFICATION_RESULT_RECORDED"
  string verification_result  = 4;  // "VALID" or "TAMPERED"
  string original_hash        = 5;
  string current_hash         = 6;
  string verified_by          = 7;  // actor_id from JWT
  string verified_at          = 8;  // ISO 8601 UTC
}

// Retrieve proof record for an artifact
message ArtifactProofRequest {
  string artifact_id = 1;
}

// Response specifically for GetProofByArtifactId.
// Returns the original hash and signature so Evidence Collector
// can perform full verification (hash comparison + VerifySignature).
message ArtifactIntegrityProofResponse {
  string record_id           = 1;
  string artifact_id         = 2;
  string case_id             = 3;
  string hash_algorithm      = 4;
  string hash_value          = 5;  // original artifact SHA-256 hash
  string signature_algorithm = 6;
  string signature_value     = 7;  // original RSA signature (base64)
  string signer_id           = 8;
  string record_hash         = 9;  // ledger chain record hash
  bool   success             = 10;
  string error_message       = 11;
}

// Ledger record response (used by AppendProofRecord and AppendVerificationRecord)
message ProofRecordResponse {
  string record_id           = 1;  // UUID v4
  string artifact_id         = 2;
  string record_type         = 3;
  string payload_hash        = 4;  // SHA-256 of record content
  string previous_record_hash = 5;
  string record_hash         = 6;  // SHA-256(payload_hash + previous_record_hash)
  string created_at          = 7;
  bool   success             = 8;
  string error_message       = 9;
}

// Validate full ledger chain integrity
message ValidateLedgerRequest {
  bool full_validation = 1;  // true = check all records
}

message ValidateLedgerResponse {
  bool   chain_valid      = 1;
  int32  checked_records  = 2;
  string error_message    = 3;
}
```

### Generating Python stubs

```bash
# Run from repo root
pip install grpcio grpcio-tools

python -m grpc_tools.protoc \
  -I proto \
  --python_out=services/evidence-collector/grpc_clients \
  --grpc_python_out=services/evidence-collector/grpc_clients \
  proto/hash_sign.proto proto/ledger.proto

python -m grpc_tools.protoc \
  -I proto \
  --python_out=services/hash-sign \
  --grpc_python_out=services/hash-sign \
  proto/hash_sign.proto

python -m grpc_tools.protoc \
  -I proto \
  --python_out=services/immutable-ledger \
  --grpc_python_out=services/immutable-ledger \
  proto/ledger.proto
```

---

## 7. RabbitMQ Topology

```
Exchange:  forensicchain.events   (type: topic, durable: true)
Queue:     custody.events.queue   (durable: true)
Binding:   forensicchain.#  →  custody.events.queue

DLX:       forensicchain.dlx      (type: direct, durable: true)
DLQ:       custody.events.dlq     (durable: true)
```

### Routing Keys

| Event | Routing Key |
|---|---|
| EvidenceIngested | `forensicchain.evidence.ingested` |
| EvidenceViewed | `forensicchain.evidence.viewed` |
| EvidenceDownloaded | `forensicchain.evidence.downloaded` |
| VerificationRequested | `forensicchain.verification.requested` |
| VerificationPassed | `forensicchain.verification.passed` |
| VerificationFailed | `forensicchain.verification.failed` |
| ReportGenerated | `forensicchain.report.generated` |
| ReportDownloaded | `forensicchain.report.downloaded` |
| ReportVerified | `forensicchain.report.verified` |

### Publisher Ownership

| Publisher | Events |
|---|---|
| Evidence Collector Service | All `forensicchain.evidence.*` and `forensicchain.verification.*` |
| Audit Reporter Service | All `forensicchain.report.*` |

### RabbitMQ Setup Code (run once on startup)

```python
# shared/rabbitmq_setup.py
import aio_pika

async def setup_rabbitmq(connection):
    channel = await connection.channel()

    # Dead letter exchange
    dlx = await channel.declare_exchange(
        "forensicchain.dlx",
        type=aio_pika.ExchangeType.DIRECT,
        durable=True
    )

    # Dead letter queue
    dlq = await channel.declare_queue(
        "custody.events.dlq",
        durable=True
    )
    await dlq.bind(dlx, routing_key="custody.events.dlq")

    # Main exchange
    exchange = await channel.declare_exchange(
        "forensicchain.events",
        type=aio_pika.ExchangeType.TOPIC,
        durable=True
    )

    # Main queue with DLX config
    # No x-message-ttl: retry logic is handled by the consumer via x-retry-count header.
    # Messages only reach DLQ after 3 failed attempts by the consumer.
    queue = await channel.declare_queue(
        "custody.events.queue",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "forensicchain.dlx",
            "x-dead-letter-routing-key": "custody.events.dlq",
        }
    )
    await queue.bind(exchange, routing_key="forensicchain.#")

    return exchange, queue
```

---

## 8. Event Schema

All events share this envelope. `payload` varies by event type.

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "EvidenceIngested",
  "routing_key": "forensicchain.evidence.ingested",
  "artifact_id": "7d5f3c1a-2b4e-4f8a-9c6d-1e3f5a7b9c2d",
  "case_id": "CASE-2026-001",
  "actor_id": "user-analyst",
  "actor_role": "ForensicAnalyst",
  "timestamp": "2026-05-14T10:30:00Z",
  "correlation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "reason": "Initial evidence ingestion",
  "payload": {}
}
```

### Payload by Event Type

**EvidenceIngested:**
```json
{
  "file_name": "phone_extraction.zip",
  "file_size": 10485760,
  "artifact_type": "MobileExtraction",
  "hash_algorithm": "SHA-256",
  "hash_value": "a3f5...c9d1",
  "ledger_record_id": "uuid"
}
```

**VerificationPassed:**
```json
{
  "verification_result": "VALID",
  "original_hash": "a3f5...c9d1",
  "current_hash": "a3f5...c9d1",
  "ledger_record_id": "uuid"
}
```

**VerificationFailed:**
```json
{
  "verification_result": "TAMPERED",
  "original_hash": "a3f5...c9d1",
  "current_hash": "b7e2...f4a8"
}
```

**ReportGenerated:**
```json
{
  "report_id": "uuid",
  "report_hash": "sha256_of_report",
  "report_format": "PDF"
}
```

**EvidenceViewed / EvidenceDownloaded / ReportDownloaded:**
```json
{
  "ip_address": "192.168.1.10"
}
```

---

## 9. REST API Contracts

All endpoints below are exposed through the gateway at `http://localhost:8080`.

### Evidence Collector (internal: `http://evidence-service:8001`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/evidence` | Investigator, ForensicAnalyst | Upload artifact |
| GET | `/evidence/{artifactId}` | Any | Get artifact metadata |
| POST | `/evidence/{artifactId}/verify` | Any | Verify artifact integrity |
| GET | `/health` | None | Health check |

**POST /evidence — Request (multipart/form-data):**
```
file        : <binary>
case_id     : "CASE-2026-001"
title       : "Phone extraction from suspect device"
artifact_type : "MobileExtraction"
description : "Optional description"
```

**POST /evidence — Response 201:**
```json
{
  "artifact_id": "uuid",
  "case_id": "CASE-2026-001",
  "file_name": "phone_extraction.zip",
  "file_size": 10485760,
  "hash_value": "a3f5...c9d1",
  "hash_algorithm": "SHA-256",
  "signature_value": "base64...",
  "ledger_record_id": "uuid",
  "status": "INGESTED",
  "uploaded_at": "2026-05-14T10:30:00Z"
}
```

**POST /evidence/{artifactId}/verify — Request (multipart/form-data):**
```
file : <binary>   (the file to check against the original)
```

**POST /evidence/{artifactId}/verify — Response 200:**
```json
{
  "artifact_id": "uuid",
  "verification_result": "VALID",
  "original_hash": "a3f5...c9d1",
  "current_hash": "a3f5...c9d1",
  "signature_valid": true,
  "ledger_chain_valid": true,
  "verified_at": "2026-05-14T11:00:00Z"
}
```

---

### Chain of Custody (internal: `http://custody-service:8004`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/custody/{artifactId}/timeline` | LegalReviewer, Any | Get custody timeline |
| GET | `/health` | None | Health check |

**GET /custody/{artifactId}/timeline — Response 200:**
```json
{
  "artifact_id": "uuid",
  "total_events": 5,
  "chain_valid": true,
  "events": [
    {
      "event_id": "uuid",
      "event_type": "EvidenceIngested",
      "actor_id": "user-analyst",
      "actor_role": "ForensicAnalyst",
      "timestamp": "2026-05-14T10:30:00Z",
      "reason": "Initial evidence ingestion",
      "ip_address": "192.168.1.10",
      "event_hash": "sha256...",
      "previous_event_hash": null
    }
  ]
}
```

---

### Audit Reporter (internal: `http://report-service:8005`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/reports/{artifactId}` | LegalReviewer | Generate report |
| GET | `/reports/{reportId}` | LegalReviewer | Retrieve report metadata |
| GET | `/reports/{reportId}/download` | LegalReviewer | Download archived PDF/HTML |
| POST | `/reports/{reportId}/verify` | LegalReviewer | Verify report hash integrity |
| GET | `/health` | None | Health check |

**POST /reports/{artifactId} — Response 201:**
```json
{
  "report_id": "uuid",
  "artifact_id": "uuid",
  "report_hash": "sha256...",
  "format": "PDF",
  "generated_at": "2026-05-14T12:00:00Z",
  "generated_by": "user-reviewer"
}
```

**GET /reports/{reportId} — Response 200 (metadata only):**
```json
{
  "report_id": "uuid",
  "artifact_id": "uuid",
  "report_hash": "sha256...",
  "format": "PDF",
  "generated_at": "2026-05-14T12:00:00Z",
  "generated_by": "user-reviewer",
  "storage_path": "/report-storage/uuid.pdf"
}
```

**GET /reports/{reportId}/download — Response 200:**
Returns the PDF/HTML binary with `Content-Type: application/pdf` (or `text/html`).
Triggers `ReportDownloaded` event publication.

**POST /reports/{reportId}/verify — Response 200:**
```json
{
  "report_id": "uuid",
  "report_valid": true,
  "stored_hash": "sha256...",
  "current_hash": "sha256...",
  "verified_at": "2026-05-14T12:30:00Z"
}
```
Recomputes the SHA-256 hash of the archived PDF and compares it with the hash stored
in `report_db`. Returns `report_valid: true` if they match. Triggers `ReportVerified` event.

---

### Immutable Ledger REST (internal: `http://ledger-service:8003`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/ledger/artifacts/{artifactId}` | Internal only | Get proof record |
| GET | `/ledger/validate` | Internal only | Validate chain |
| GET | `/health` | None | Health check |

---

## 10. Database Schemas

### evidence_db — Evidence Collector

```sql
-- UUIDs are generated in Python (uuid.uuid4()) and passed explicitly.
-- No gen_random_uuid() dependency, no pgcrypto extension required.
CREATE TABLE artifacts (
    artifact_id       UUID PRIMARY KEY,
    case_id           VARCHAR(64) NOT NULL,
    file_name         VARCHAR(512) NOT NULL,
    file_size         BIGINT NOT NULL,
    artifact_type     VARCHAR(64) NOT NULL,
    storage_path      VARCHAR(1024) NOT NULL,
    description       TEXT,
    uploaded_by       VARCHAR(64) NOT NULL,
    uploaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status            VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    -- status: PENDING | INGESTED | INGESTION_FAILED
    hash_value        VARCHAR(256),
    hash_algorithm    VARCHAR(32),
    signature_value   TEXT,
    ledger_record_id  UUID,
    correlation_id    UUID
);

CREATE TABLE outbox_events (
    id              BIGSERIAL PRIMARY KEY,
    event_id        UUID NOT NULL UNIQUE,
    event_type      VARCHAR(128) NOT NULL,
    routing_key     VARCHAR(256) NOT NULL,
    payload         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published       BOOLEAN NOT NULL DEFAULT FALSE,
    published_at    TIMESTAMPTZ,
    retry_count     INT NOT NULL DEFAULT 0
);

CREATE INDEX idx_outbox_unpublished ON outbox_events (published, created_at)
    WHERE published = FALSE;
```

### ledger_db — Immutable Ledger

```sql
CREATE TABLE ledger_records (
    record_id             UUID PRIMARY KEY,          -- generated in Python with uuid.uuid4()
    artifact_id           UUID NOT NULL,
    case_id               VARCHAR(64) NOT NULL,
    record_type           VARCHAR(64) NOT NULL,
    -- record_type: EVIDENCE_PROOF_CREATED | VERIFICATION_RESULT_RECORDED
    -- Explicit integrity fields for fast retrieval by GetProofByArtifactId
    hash_algorithm        VARCHAR(32),               -- e.g. "SHA-256"
    hash_value            VARCHAR(256),              -- original artifact hash (hex)
    signature_algorithm   VARCHAR(32),               -- e.g. "RSA-SHA256"
    signature_value       TEXT,                      -- original signature (base64)
    signer_id             VARCHAR(128),              -- "hash-sign-service"
    -- Hash-chain fields
    payload_hash          VARCHAR(256) NOT NULL,
    previous_record_hash  VARCHAR(256),              -- NULL for first record
    record_hash           VARCHAR(256) NOT NULL,
    raw_payload           JSONB NOT NULL,            -- full proof data for audit
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ledger_state: single-row table used as a mutex for hash-chain appends.
-- Concurrent ingestion requests both try to read the last record_hash to set
-- as previous_record_hash for the new record. Without locking, two concurrent
-- requests can read the same "last record" and produce two records with the same
-- previous_record_hash, breaking chain continuity.
--
-- Solution: SELECT ... FOR UPDATE on this row serialises all appends so only
-- one transaction holds the lock at a time. The update is lightweight (one row,
-- one column); it does not block reads of ledger_records itself.
CREATE TABLE ledger_state (
    id               INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- single-row enforced
    last_record_hash VARCHAR(256),          -- NULL until first record is appended
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Safe to run multiple times (e.g. idempotent init scripts / migrations):
INSERT INTO ledger_state (id, last_record_hash)
VALUES (1, NULL)
ON CONFLICT (id) DO NOTHING;

CREATE INDEX idx_ledger_artifact ON ledger_records (artifact_id, created_at);
```

**Ledger append pattern (append_proof_record in servicer.py):**
```python
def AppendProofRecord(self, request, context):
    with db.begin():
        # Lock the single ledger_state row — all other append attempts
        # block here until this transaction commits or rolls back.
        state = db.execute(
            "SELECT last_record_hash FROM ledger_state WHERE id = 1 FOR UPDATE"
        ).fetchone()
        previous_record_hash = state["last_record_hash"]

        payload_hash, record_hash = compute_record_hash(
            build_payload(request), previous_record_hash
        )
        record_id = str(uuid.uuid4())

        db.execute(INSERT_LEDGER_RECORD, {
            "record_id": record_id,
            "previous_record_hash": previous_record_hash,
            "record_hash": record_hash,
            ...
        })
        db.execute(
            "UPDATE ledger_state SET last_record_hash = :h, updated_at = NOW() WHERE id = 1",
            {"h": record_hash}
        )
    # Transaction committed; lock released
    return ProofRecordResponse(record_id=record_id, record_hash=record_hash, success=True)
```

### custody_db — Chain of Custody

```sql
CREATE TABLE custody_events (
    id                  BIGSERIAL PRIMARY KEY,
    event_id            UUID NOT NULL UNIQUE,
    artifact_id         UUID NOT NULL,
    case_id             VARCHAR(64),
    actor_id            VARCHAR(64) NOT NULL,
    actor_role          VARCHAR(64) NOT NULL,
    event_type          VARCHAR(128) NOT NULL,
    timestamp           TIMESTAMPTZ NOT NULL,
    reason              TEXT,
    ip_address          VARCHAR(64),
    correlation_id      UUID,
    payload             JSONB,
    previous_event_hash VARCHAR(256),
    event_hash          VARCHAR(256) NOT NULL,
    received_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE processed_event_ids (
    event_id    UUID PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_custody_artifact ON custody_events (artifact_id, timestamp);
```

### report_db — Audit Reporter

```sql
-- report_id generated in Python (uuid.uuid4()), passed explicitly.
CREATE TABLE reports (
    report_id       UUID PRIMARY KEY,
    artifact_id     UUID NOT NULL,
    case_id         VARCHAR(64),
    generated_by    VARCHAR(64) NOT NULL,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    format          VARCHAR(16) NOT NULL DEFAULT 'PDF',
    report_hash     VARCHAR(256) NOT NULL,
    storage_path    VARCHAR(1024),   -- path to archived PDF under /report-storage/
    correlation_id  UUID
);

CREATE INDEX idx_reports_artifact ON reports (artifact_id, generated_at);
```

---

## 11. JWT & Authentication Strategy

### Key Generation

```bash
# Generate RSA key pair for artifact signing (Hash & Sign Service)
openssl genrsa -out keys/private_key.pem 2048
openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem
```

### Demo Token Generation

```python
# scripts/generate_demo_tokens.py
import jwt
import datetime
import os

SECRET = os.getenv("JWT_SECRET", "dev-secret-key")

users = [
    {"sub": "user-investigator",  "role": "Investigator",    "name": "Demo Investigator"},
    {"sub": "user-analyst",       "role": "ForensicAnalyst", "name": "Demo Analyst"},
    {"sub": "user-reviewer",      "role": "LegalReviewer",   "name": "Demo Reviewer"},
    {"sub": "user-admin",         "role": "Admin",           "name": "Demo Admin"},
]

print("=" * 80)
print("FORENSICCHAIN DEMO JWT TOKENS")
print("Algorithm: HS256 | Expiry: 30 days")
print("=" * 80)

for user in users:
    payload = {
        **user,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30),
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    print(f"\n{user['role']}:")
    print(f"  Bearer {token}")

print("\n" + "=" * 80)
print("Usage: curl -H 'Authorization: Bearer <token>' http://localhost:8080/evidence")
```

Run: `JWT_SECRET=dev-secret-key python scripts/generate_demo_tokens.py`

### Authentication Architecture

External authentication is handled entirely by the Nginx `auth_request` flow.
Downstream services **trust the forwarded headers** (`X-User-Id`, `X-User-Role`,
`X-Correlation-Id`) set by the gateway after successful token validation. They
do not re-decode the JWT themselves in normal operation.

Direct JWT decoding middleware (`decode_jwt` below) is provided **only** for
local development and direct service debugging (bypassing the gateway). It must
not be registered as a mandatory dependency in production paths.

```python
# services/<service>/auth/middleware.py
# Used ONLY for local development / direct-service debugging.
# In normal gateway-routed requests, use request.headers.get("X-User-Id") etc.

import jwt
import os
from fastapi import Request, HTTPException

JWT_SECRET    = os.getenv("JWT_SECRET", "dev-secret-key")
JWT_ALGORITHM = "HS256"

def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_identity_from_headers(request: Request) -> dict:
    """
    Primary method — read identity from headers forwarded by the gateway.
    Falls back to token decode only when gateway headers are absent
    (e.g. direct curl during development).
    """
    user_id  = request.headers.get("X-User-Id")
    user_role = request.headers.get("X-User-Role")
    if user_id and user_role:
        return {"sub": user_id, "role": user_role}
    # Dev fallback: decode token directly
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return decode_jwt(auth[7:])
    raise HTTPException(status_code=401, detail="Missing identity headers")
```

### Nginx Gateway Configuration

```nginx
# services/gateway/nginx.conf

events { worker_connections 1024; }

http {

    # Allow large evidence file uploads (forensic images, mobile extractions, etc.)
    client_max_body_size 100M;

    upstream evidence_service  { server evidence-service:8001; }
    upstream custody_service   { server custody-service:8004; }
    upstream report_service    { server report-service:8005; }
    upstream ledger_service    { server ledger-service:8003; }

    server {
        listen 8080;
        server_name localhost;

        # Internal auth validation endpoint
        # Points to a small /internal/auth/validate endpoint
        # in the evidence-collector service (or standalone)
        location = /internal/auth/validate {
            internal;
            proxy_pass              http://evidence_service/internal/auth/validate;
            proxy_pass_request_body off;
            proxy_set_header        Content-Length "";
            proxy_set_header        X-Original-URI $request_uri;
            # Forward Authorization header so the validate endpoint can decode the JWT
            proxy_set_header        Authorization $http_authorization;
            # Forward HTTP method so RBAC can distinguish GET vs POST on the same path
            proxy_set_header        X-Original-Method $request_method;
        }

        # Evidence endpoints
        location /evidence {
            auth_request /internal/auth/validate;
            auth_request_set $user_id   $upstream_http_x_user_id;
            auth_request_set $user_role $upstream_http_x_user_role;
            auth_request_set $corr_id   $upstream_http_x_correlation_id;

            proxy_set_header X-User-Id        $user_id;
            proxy_set_header X-User-Role      $user_role;
            proxy_set_header X-Correlation-Id $corr_id;

            proxy_pass http://evidence_service;
        }

        # Custody timeline
        location /custody {
            auth_request /internal/auth/validate;
            auth_request_set $user_id   $upstream_http_x_user_id;
            auth_request_set $user_role $upstream_http_x_user_role;
            auth_request_set $corr_id   $upstream_http_x_correlation_id;

            proxy_set_header X-User-Id        $user_id;
            proxy_set_header X-User-Role      $user_role;
            proxy_set_header X-Correlation-Id $corr_id;

            proxy_pass http://custody_service;
        }

        # Reports
        location /reports {
            auth_request /internal/auth/validate;
            auth_request_set $user_id   $upstream_http_x_user_id;
            auth_request_set $user_role $upstream_http_x_user_role;
            auth_request_set $corr_id   $upstream_http_x_correlation_id;

            proxy_set_header X-User-Id        $user_id;
            proxy_set_header X-User-Role      $user_role;
            proxy_set_header X-Correlation-Id $corr_id;

            proxy_pass http://report_service;
        }

        # Ledger validation (internal use, still gated)
        location /ledger {
            auth_request /internal/auth/validate;
            proxy_pass http://ledger_service;
        }

        # Health checks (no auth)
        # NOTE: This endpoint proxies to Evidence Service only. It confirms that
        # the gateway can reach Evidence Service, not that all services are healthy.
        # During development, check each service's own /health endpoint directly
        # on its host port. Before demo, verify gateway connectivity only.
        location /health {
            proxy_pass http://evidence_service/health;
        }
    }
}
```

**Internal auth validation endpoint** (add to Evidence Collector):

```python
# In evidence-collector/routers/internal.py
from fastapi import APIRouter, Request, Response
import jwt, os, uuid

router = APIRouter(prefix="/internal")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key")

# Role → list of rule tuples.
# 2-tuple  (method, path_prefix)        : method + prefix match only.
# 3-tuple  (method, path_prefix, suffix): also requires uri.endswith(suffix).
# The 3-tuple form prevents a role from accessing other endpoints that share
# the same prefix — e.g. LegalReviewer can POST to /evidence/.../verify but
# not to /evidence/ (upload) or any future POST /evidence/.../other endpoint.
ROLE_RULES: dict[str, list[tuple]] = {
    "Investigator": [
        ("POST", "/evidence"),
        ("GET",  "/evidence/"),
    ],
    "ForensicAnalyst": [
        ("POST", "/evidence"),
        ("GET",  "/evidence/"),
    ],
    "LegalReviewer": [
        ("GET",  "/custody/"),
        ("POST", "/reports/"),           # generate report
        ("GET",  "/reports/"),           # metadata + download + verify
        ("POST", "/evidence/", "/verify"),  # only POST .../verify, not upload
    ],
    "Admin": [
        ("GET",  "/"),
        ("POST", "/"),
    ],
}

@router.get("/auth/validate")
async def validate_token(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return Response(status_code=401)
    try:
        payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=["HS256"])
        role    = payload.get("role", "")
        uri     = request.headers.get("X-Original-URI", "")
        method  = request.headers.get("X-Original-Method", "GET").upper()

        # Method + path prefix (+ optional suffix) RBAC check
        rules = ROLE_RULES.get(role, [])
        allowed = any(
            method == rule[0]
            and uri.startswith(rule[1])
            and (len(rule) == 2 or uri.endswith(rule[2]))
            for rule in rules
        )
        if not allowed:
            return Response(status_code=403)

        corr_id  = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
        response = Response(status_code=200)
        response.headers["X-User-Id"]        = payload.get("sub", "")
        response.headers["X-User-Role"]      = role
        response.headers["X-Correlation-Id"] = corr_id
        return response
    except Exception:
        return Response(status_code=401)
```

---

## 12. Service-by-Service Implementation Guide

### Person A: Evidence Collector Service

**Minimum viable implementation:**

```python
# services/evidence-collector/main.py
from fastapi import FastAPI
from routers import evidence, internal
from db.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ForensicChain — Evidence Collector")
app.include_router(evidence.router)
app.include_router(internal.router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "evidence-collector"}
```

**Upload flow (evidence/router.py):**

```python
@router.post("/evidence", status_code=201)
async def upload_evidence(
    file: UploadFile,
    case_id: str = Form(...),
    title: str = Form(...),
    artifact_type: str = Form(...),
    description: str = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    actor_id   = request.headers.get("X-User-Id", "unknown")
    actor_role = request.headers.get("X-User-Role", "unknown")
    corr_id    = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))

    artifact_id = str(uuid.uuid4())

    # 1. Save file to shared volume (chunked write — avoids loading entire file into memory)
    storage_path = f"/evidence-storage/{artifact_id}/original.bin"
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    file_size = 0
    with open(storage_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            f.write(chunk)
            file_size += len(chunk)

    # 2. Write PENDING artifact to DB
    artifact = create_artifact(db, artifact_id, case_id, file.filename,
                               file_size, artifact_type, storage_path,
                               description, actor_id, corr_id)

    # 3. Call Hash & Sign via gRPC
    proof = hash_sign_client.compute_and_sign(
        artifact_id=artifact_id,
        case_id=case_id,
        file_path=storage_path,
        file_name=file.filename,
        file_size=file_size,
    )
    if not proof.success:
        update_artifact_status(db, artifact_id, "INGESTION_FAILED")
        os.remove(storage_path)
        raise HTTPException(503, "Hash & Sign failed")

    # 4. Append to Ledger via gRPC
    ledger_record = ledger_client.append_proof(
        artifact_id=artifact_id,
        case_id=case_id,
        hash_value=proof.hash_value,
        signature_value=proof.signature_value,
        ...
    )
    if not ledger_record.success:
        update_artifact_status(db, artifact_id, "INGESTION_FAILED")
        raise HTTPException(503, "Ledger append failed")

    # 5. Update artifact to INGESTED + write outbox event (same transaction)
    update_artifact_ingested(db, artifact_id, proof, ledger_record.record_id)
    write_outbox_event(db, artifact_id, case_id, "EvidenceIngested",
                       "forensicchain.evidence.ingested", actor_id, actor_role,
                       corr_id, payload={...})
    db.commit()

    return {...}
```

**Outbox publisher (background task):**

```python
# services/evidence-collector/rabbitmq/outbox_publisher.py
import asyncio
import aio_pika

# OUTBOX PAYLOAD RULE:
# outbox_events.payload stores the FULL event envelope — not only the inner
# event-specific payload. The published RabbitMQ message body must contain
# event_id, event_type, routing_key, artifact_id, case_id, actor_id,
# actor_role, timestamp, correlation_id, reason, and payload.
# Chain of Custody consumer reads body["event_id"], body["event_type"],
# body["artifact_id"] etc. directly — if only the inner payload were stored,
# all those lookups would fail with KeyError.
async def publish_outbox_events(db, channel, exchange):
    """
    Poll outbox_events where published=False, publish to RabbitMQ,
    mark as published. Run every 2 seconds.
    """
    while True:
        unpublished = db.query(OutboxEvent)\
            .filter_by(published=False)\
            .order_by(OutboxEvent.created_at)\
            .limit(10).all()

        for event in unpublished:
            try:
                # event.payload is the full envelope (see OUTBOX PAYLOAD RULE above)
                await exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(event.payload).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        content_type="application/json",
                    ),
                    routing_key=event.routing_key,
                )
                event.published = True
                event.published_at = datetime.utcnow()
            except Exception as e:
                event.retry_count += 1
        db.commit()
        await asyncio.sleep(2)
```

---

### Person A: Hash & Sign Service

```python
# services/hash-sign/servicer.py
import hashlib, base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import hash_sign_pb2_grpc  # generated by protoc

# Server-side: inherit from the generated Servicer base class, NOT the Stub.
# HashSignServiceStub is the client-side stub — using it on the server side
# would cause an import error or silent method-not-found failures.
class HashSignServicer(hash_sign_pb2_grpc.HashSignServiceServicer):

    def __init__(self):
        with open("/keys/private_key.pem", "rb") as f:
            self.private_key = serialization.load_pem_private_key(f.read(), password=None)

    def ComputeAndSignHash(self, request, context):
        try:
            with open(request.file_path, "rb") as f:
                content = f.read()

            sha256 = hashlib.sha256(content).hexdigest()

            signature = self.private_key.sign(
                sha256.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            sig_b64 = base64.b64encode(signature).decode()

            return IntegrityProofResponse(
                artifact_id=request.artifact_id,
                case_id=request.case_id,
                hash_algorithm="SHA-256",
                hash_value=sha256,
                signature_algorithm="RSA-SHA256",
                signature_value=sig_b64,
                signer_id="hash-sign-service",
                signed_at=datetime.utcnow().isoformat() + "Z",
                success=True,
            )
        except Exception as e:
            return IntegrityProofResponse(success=False, error_message=str(e))

    def RecomputeHash(self, request, context):
        try:
            with open(request.file_path, "rb") as f:
                content = f.read()
            sha256 = hashlib.sha256(content).hexdigest()
            return HashResponse(
                artifact_id=request.artifact_id,
                hash_algorithm="SHA-256",
                hash_value=sha256,
                success=True,
            )
        except Exception as e:
            return HashResponse(success=False, error_message=str(e))

    # TODO — DO NOT leave this as a placeholder before demo or submission.
    # Returning signature_valid=True without actual verification creates a
    # false sense of security: the verification endpoint would always report
    # VALID regardless of whether the signature matches, making the entire
    # signature check meaningless.
    # This method MUST load the public key and call public_key.verify(...).
    def VerifySignature(self, request, context):
        try:
            # Load public key from /keys/public_key.pem
            # Decode base64 signature_value
            # Verify: public_key.verify(signature_bytes, request.hash_value.encode(),
            #                           padding.PKCS1v15(), hashes.SHA256())
            # If verify() does not raise, the signature is valid.
            # ⚠ Remove the placeholder return below once the above is implemented.
            return SignatureVerifyResponse(
                artifact_id=request.artifact_id,
                signature_valid=True,   # ⚠ PLACEHOLDER — replace with real verify()
                success=True,
            )
        except Exception as e:
            return SignatureVerifyResponse(
                artifact_id=request.artifact_id,
                signature_valid=False,
                success=False,
                error_message=str(e),
            )
    # All three RPC methods (ComputeAndSignHash, RecomputeHash, VerifySignature)
    # must be fully implemented before the verification endpoint can work end-to-end.
```

---

### Person A: Immutable Ledger Service

```python
# services/immutable-ledger/chain/hash_chain.py
import hashlib, json

def compute_record_hash(payload: dict, previous_record_hash: str | None) -> tuple[str, str]:
    """
    Returns (payload_hash, record_hash).
    payload_hash  = SHA-256(json.dumps(payload, sort_keys=True))
    record_hash   = SHA-256(payload_hash + (previous_record_hash or "GENESIS"))
    """
    payload_str  = json.dumps(payload, sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
    prev         = previous_record_hash or "GENESIS"
    record_hash  = hashlib.sha256((payload_hash + prev).encode()).hexdigest()
    return payload_hash, record_hash

def validate_chain(records: list[dict]) -> bool:
    """
    records: list of dicts with keys: payload_hash, previous_record_hash, record_hash, raw_payload
    Returns True if entire chain is intact.

    NOTE: This function iterates all ledger records. For the MVP dataset this is
    acceptable. In a larger deployment, calling full chain validation on every
    verification request would be expensive. Prefer artifact-scoped proof
    validation (verify only the records belonging to one artifact) or run full
    validation as a periodic background job instead of on every request.
    """
    for i, record in enumerate(records):
        expected_prev = records[i-1]["record_hash"] if i > 0 else None
        if record["previous_record_hash"] != expected_prev:
            return False
        _, expected_hash = compute_record_hash(
            record["raw_payload"],
            record["previous_record_hash"]
        )
        if record["record_hash"] != expected_hash:
            return False
    return True
```

---

### Person B: Chain of Custody Service

```python
# services/chain-of-custody/consumer.py
import aio_pika, json, hashlib

async def consume_events(connection, db):
    channel = await connection.channel()

    # Get the main exchange for re-publishing retries with the correct routing key.
    # channel.default_exchange only handles direct queue-name routing and cannot
    # deliver to a topic exchange — so we must get forensicchain.events explicitly.
    exchange = await channel.get_exchange("forensicchain.events")
    queue    = await channel.get_queue("custody.events.queue")

    async with queue.iterator() as q:
        async for message in q:
            retry_count = int((message.headers or {}).get("x-retry-count", 0))
            # retry_count starts at 0 (first delivery).
            # With count < 3: attempts = initial + 3 retries = 4 total before DLQ.
            # To cap at 3 total attempts, change the condition to: retry_count < 2.
            try:
                body = json.loads(message.body)
                event_id = body["event_id"]

                # Idempotency check
                if is_already_processed(db, event_id):
                    await message.ack()
                    continue

                # Per-artifact hash chain — include ALL meaningful fields
                # so any modification to reason, ip_address, payload etc. breaks the chain
                prev = get_last_event_hash(db, body["artifact_id"])
                event_content = {
                    "event_id":            body["event_id"],
                    "event_type":          body["event_type"],
                    "artifact_id":         body["artifact_id"],
                    "case_id":             body.get("case_id"),
                    "actor_id":            body["actor_id"],
                    "actor_role":          body["actor_role"],
                    "timestamp":           body["timestamp"],
                    "reason":              body.get("reason"),
                    "ip_address":          body.get("payload", {}).get("ip_address"),
                    "correlation_id":      body.get("correlation_id"),
                    "payload":             body.get("payload", {}),
                    "previous_event_hash": prev,
                }
                event_hash = hashlib.sha256(
                    json.dumps(event_content, sort_keys=True).encode()
                ).hexdigest()

                # Write custody event
                insert_custody_event(db, body, prev, event_hash)
                mark_processed(db, event_id)
                db.commit()
                await message.ack()

            except Exception:
                if retry_count < 3:
                    # Publish a retry copy via the main topic exchange with the
                    # original routing key so it reaches custody.events.queue again.
                    # Then ack the original — the retry copy is now the live message.
                    new_headers = dict(message.headers or {})
                    new_headers["x-retry-count"] = retry_count + 1
                    await exchange.publish(
                        aio_pika.Message(
                            body=message.body,
                            headers=new_headers,
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            content_type="application/json",
                        ),
                        routing_key=message.routing_key,
                    )
                    await message.ack()   # original consumed; retry copy is live
                else:
                    # 3 attempts exhausted → reject so RabbitMQ forwards to DLX/DLQ
                    await message.reject(requeue=False)
```

---

### Person B: Audit Reporter Service

```python
# services/audit-reporter/report_generator.py
import httpx, hashlib

async def generate_report(artifact_id: str, actor_id: str, actor_role: str, corr_id: str):
    headers = {
        "X-User-Id": actor_id,
        "X-User-Role": actor_role,
        "X-Correlation-Id": corr_id,
    }

    async with httpx.AsyncClient() as client:
        # 1. Pull artifact metadata
        artifact = (await client.get(
            f"{EVIDENCE_SERVICE_URL}/evidence/{artifact_id}", headers=headers
        )).json()

        # 2. Pull ledger proof
        ledger = (await client.get(
            f"{LEDGER_SERVICE_URL}/ledger/artifacts/{artifact_id}", headers=headers
        )).json()

        # 3. Pull custody timeline
        timeline = (await client.get(
            f"{CUSTODY_SERVICE_URL}/custody/{artifact_id}/timeline", headers=headers
        )).json()

    # 4. Render HTML/PDF
    report_bytes = render_pdf(artifact, ledger, timeline)

    # 5. Compute report hash
    report_hash = hashlib.sha256(report_bytes).hexdigest()

    return report_bytes, report_hash
```

---

## 13. Error Handling Decisions

| Scenario | Behavior |
|---|---|
| File write to volume fails | Return 500, no DB record created |
| Hash & Sign gRPC fails | Return 503, artifact marked `INGESTION_FAILED`, file deleted |
| Ledger append gRPC fails | Return 503, artifact marked `INGESTION_FAILED` |
| RabbitMQ publish fails | Ingestion confirmed (hash+ledger succeeded). Event stored in outbox, retried every 2s |
| Duplicate upload (same file) | Allowed. New `artifact_id` generated each time |
| Chain of Custody receives duplicate event | `event_id` checked in `processed_event_ids`, duplicate silently dropped |
| Chain of Custody consumer fails after initial attempt + 3 retries (4 total) | Message sent to `custody.events.dlq` |
| Audit Reporter cannot reach a service | Return 503, report not generated |
| Verification: file not found in volume | Return 404 |

---

## 14. Integration Order & Milestones

Work in this order. Do not skip ahead — each step validates the previous one.

```
Milestone 1 — Infrastructure (Day 1)
  [ ] docker-compose.yml runs: all DBs + RabbitMQ healthy
  [ ] All services return GET /health → {"status": "ok"}
  [ ] Demo tokens generated, Nginx starts

Milestone 2 — Minimal ingestion (Day 2-3)
  [ ] POST /evidence → file saved to volume
  [ ] Evidence Collector calls Hash & Sign gRPC → hash + signature returned
  [ ] Evidence Collector calls Ledger gRPC → ledger record appended
  [ ] Artifact status = INGESTED in evidence_db
  [ ] EvidenceIngested event in outbox_events (published = false)
  TEST: curl -X POST http://localhost:8080/evidence -H "Authorization: Bearer <analyst_token>" -F "file=@test.zip" -F "case_id=CASE-001" -F "artifact_type=MobileExtraction" -F "title=Test"

Milestone 3 — Event flow (Day 3-4)
  [ ] Outbox publisher runs, publishes EvidenceIngested to RabbitMQ
  [ ] Chain of Custody consumer receives event
  [ ] Custody event written to custody_db with event_hash
  TEST: curl http://localhost:8080/custody/{artifactId}/timeline

Milestone 4 — Verification (Day 4-5)
  [ ] VerifySignature RPC fully implemented in Hash & Sign Service:
      load /keys/public_key.pem, base64-decode signature_value,
      call public_key.verify(...) — do NOT leave the placeholder stub
  [ ] POST /evidence/{artifactId}/verify with original file → VALID
  [ ] POST /evidence/{artifactId}/verify with modified file → TAMPERED
  [ ] VerificationPassed / VerificationFailed event in custody timeline
  TEST: Modify one byte of test.zip, re-upload for verification

Milestone 5 — Report generation (Day 5-6)
  [ ] POST /reports/{artifactId} → report generated, PDF archived to /report-storage/
  [ ] Report hash computed and stored in report_db
  [ ] ReportGenerated event in custody timeline
  [ ] GET /reports/{reportId} → report metadata returned (JSON)
  [ ] GET /reports/{reportId}/download → PDF binary returned, ReportDownloaded event fired
  [ ] POST /reports/{reportId}/verify → report_valid: true/false, ReportVerified event fired
  TEST: Verify custody timeline includes ReportGenerated, ReportDownloaded, ReportVerified

Milestone 6 — Full demo flow (Day 7)
  [ ] Complete scenario from upload to tamper detection to report
  [ ] All chain validations return true
  [ ] Audit trail complete in custody timeline
  [ ] Demo JWT tokens working for all 4 roles
  [ ] PRE-DEMO: In docker-compose.yml, comment out "ports:" on all internal
      services (evidence-service, hash-sign-service, ledger-service,
      custody-service, report-service) and uncomment their "expose:" blocks.
      Also comment out "ports:" on all four PostgreSQL databases
      (evidence-db, ledger-db, custody-db, report-db) — they remain reachable
      internally via their service names (evidence-db:5432 etc.).
      Also close RabbitMQ AMQP port 5672 to host (switch to "expose: - 5672").
      Internal services reach rabbitmq:5672 via Docker network — no host binding needed.
      Only gateway:8080 and (optionally) rabbitmq:15672 should be host-accessible.
      Restart: docker compose down && docker compose up --build
      Verify: curl http://localhost:8001/health must return connection refused.
              curl http://localhost:5672 must return connection refused.
              psql -h localhost -p 5433 must return connection refused.
              curl http://localhost:8080/health must return 200.
```

---

## 15. Demo Scenario

**Scenario: Unauthorized Access Investigation**

```
Case:     CASE-2026-001
Artifact: phone_extraction_original.zip
```

**Step 1 — Upload evidence**
```bash
curl -X POST http://localhost:8080/evidence \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -F "file=@phone_extraction_original.zip" \
  -F "case_id=CASE-2026-001" \
  -F "artifact_type=MobileExtraction" \
  -F "title=Phone extraction from suspect device"
# → 201: artifact_id, hash_value, status=INGESTED
```

**Step 2 — View custody timeline**
```bash
curl http://localhost:8080/custody/{artifactId}/timeline \
  -H "Authorization: Bearer $REVIEWER_TOKEN"
# → Events: EvidenceIngested (chain_valid: true)
```

**Step 3 — Verify original file (should pass)**
```bash
curl -X POST http://localhost:8080/evidence/{artifactId}/verify \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -F "file=@phone_extraction_original.zip"
# → verification_result: VALID
```

**Step 4 — Simulate tampering**
```bash
# Modify one byte of the zip to create tampered version
python -c "
data = open('phone_extraction_original.zip','rb').read()
tampered = data[:100] + b'X' + data[101:]
open('phone_extraction_tampered.zip','wb').write(tampered)
"

curl -X POST http://localhost:8080/evidence/{artifactId}/verify \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -F "file=@phone_extraction_tampered.zip"
# → verification_result: TAMPERED, original_hash ≠ current_hash
```

**Step 5 — Generate forensic audit report**
```bash
curl -X POST http://localhost:8080/reports/{artifactId} \
  -H "Authorization: Bearer $REVIEWER_TOKEN"
# → 201: report_id, report_hash

# Download the archived PDF
curl http://localhost:8080/reports/{reportId}/download \
  -H "Authorization: Bearer $REVIEWER_TOKEN" \
  --output forensic_report.pdf
# → PDF binary; triggers ReportDownloaded event

# Verify the report has not been tampered with since generation
curl -X POST http://localhost:8080/reports/{reportId}/verify \
  -H "Authorization: Bearer $REVIEWER_TOKEN"
# → report_valid: true; triggers ReportVerified event
```

**Step 6 — View final custody timeline**
```bash
curl http://localhost:8080/custody/{artifactId}/timeline \
  -H "Authorization: Bearer $REVIEWER_TOKEN"
# → Events: Ingested → VerificationPassed → VerificationFailed
#           → ReportGenerated → ReportDownloaded → ReportVerified
# → chain_valid: true for all
```

---

*This document is the single source of truth for all implementation decisions.*  
*Update it together. Commit it with every significant change.*
