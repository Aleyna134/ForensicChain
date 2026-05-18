# ForensicChain — Service Ports Reference

All services communicate over the `forensicchain_net` Docker bridge network using their container names as hostnames. Only the API Gateway and RabbitMQ management UI are exposed to the host in production/demo mode.

---

## Application Services

| Service | Container Name | Protocol | Internal Port | Dev Host Port | Demo Host Port | Notes |
|---|---|---|---|---|---|---|
| API Gateway | `api-gateway` | HTTP | 8080 | **8080** | **8080** | Always host-accessible; entry point for all external traffic |
| Evidence Collector | `evidence-service` | HTTP/REST | 8001 | 8001 | — | Routes: `/evidence/*`, `/internal/auth/*` |
| Hash & Sign | `hash-sign-service` | gRPC | 50051 | 50051 | — | ComputeAndSignHash, RecomputeHash, VerifySignature |
| Immutable Ledger | `ledger-service` | gRPC | 50052 | 50052 | — | AppendProofRecord, AppendVerificationRecord, GetProofByArtifactId, ValidateLedgerChain |
| Immutable Ledger | `ledger-service` | HTTP/REST | 8003 | 8003 | — | `GET /ledger/artifacts/{artifactId}` (used by Audit Reporter) |
| Chain of Custody | `custody-service` | HTTP/REST | 8004 | 8004 | — | Routes: `/custody/*` |
| Audit Reporter | `report-service` | HTTP/REST | 8005 | 8005 | — | Routes: `/reports/*` |
| Outbox Worker | `outbox-worker` | — | — | — | — | No HTTP port; polls outbox_events table and publishes to RabbitMQ |

---

## Databases

All databases listen on port 5432 internally. The host-side port numbers differ to avoid conflicts when running multiple Postgres instances locally.

| Database | Container Name | Internal Port | Dev Host Port | Demo Host Port |
|---|---|---|---|---|
| Evidence DB | `evidence-db` | 5432 | 5433 | — |
| Ledger DB | `ledger-db` | 5432 | 5434 | — |
| Custody DB | `custody-db` | 5432 | 5435 | — |
| Report DB | `report-db` | 5432 | 5436 | — |

Connection strings (internal, used by services):
```
evidence_db  : postgresql://<user>:<pass>@evidence-db:5432/evidence_db
ledger_db    : postgresql://<user>:<pass>@ledger-db:5432/ledger_db
custody_db   : postgresql://<user>:<pass>@custody-db:5432/custody_db
report_db    : postgresql://<user>:<pass>@report-db:5432/report_db
```

---

## Message Broker

| Container Name | Protocol | Internal Port | Dev Host Port | Demo Host Port | Notes |
|---|---|---|---|---|---|
| `rabbitmq` | AMQP | 5672 | 5672 | — | Services connect via `rabbitmq:5672` on Docker network |
| `rabbitmq` | HTTP (Management UI) | 15672 | **15672** | **15672** | Always host-accessible for monitoring |

---

## Demo Mode vs Development Mode

In **development mode** the host ports in the "Dev Host Port" column are active, allowing direct access to individual services for debugging (curl, grpcurl, psql, DBeaver, etc.).

In **demo / production mode** only the two starred entries remain host-accessible:
- `api-gateway:8080` — the sole entry point for all API calls
- `rabbitmq:15672` — management UI for monitoring

To switch between modes, toggle the `ports:` / `expose:` blocks in `docker-compose.yml` per the comments in that file. After any change run:

```bash
docker compose down --volumes --remove-orphans
docker compose up --build -d
```

---

## Internal Service URLs (used in .env / service config)

```
EVIDENCE_SERVICE_URL = http://evidence-service:8001
LEDGER_SERVICE_URL   = http://ledger-service:8003
CUSTODY_SERVICE_URL  = http://custody-service:8004

HASH_SIGN_GRPC_HOST  = hash-sign-service
HASH_SIGN_GRPC_PORT  = 50051
LEDGER_GRPC_HOST     = ledger-service
LEDGER_GRPC_PORT     = 50052

RABBITMQ_URL         = amqp://guest:guest@rabbitmq:5672/
```
