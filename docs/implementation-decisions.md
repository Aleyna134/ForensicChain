# ForensicChain — Implementation Decisions

These decisions are final. Do not change them unilaterally — discuss first, update this document together.

## 1. FILE TRANSFER
Evidence Collector saves uploaded binary to shared Docker volume at:
`/evidence-storage/{artifact_id}/original.bin`
Hash & Sign Service accesses the file via shared volume (read-only mount).
No binary bytes transferred over gRPC. No streaming in MVP.

## 2. GRPC CONTRACTS
Two proto files: `proto/hash_sign.proto` and `proto/ledger.proto`
`ArtifactHashRequest` uses `file_path` (string), not bytes content.
Timestamp fields use string (ISO 8601) in MVP for simplicity.

## 3. RABBITMQ
```
Exchange name : forensicchain.events
Exchange type : topic
Durable       : true
Main queue    : custody.events.queue
Binding       : forensicchain.#  (catches all routing keys)
DLX exchange  : forensicchain.dlx
DLQ queue     : custody.events.dlq
Routing key format: forensicchain.<domain>.<action>
```
Retry strategy: consumer tracks `x-retry-count` header.
On failure: if `retry_count < 3`, publish a retry copy with `x-retry-count+1` to
`forensicchain.events` (same routing key), then ack the original message.
After `retry_count` reaches 3, reject with `requeue=False` so RabbitMQ routes
it to the DLQ via `forensicchain.dlx`.
Total attempts = 1 initial + 3 retries = 4 attempts before DLQ.

## 4. EVENT ENVELOPE
All events share the same JSON envelope (see `docs/event-schema.md`).
`event_id`, `artifact_id`, `correlation_id`: UUID v4.
Timestamp: ISO 8601 UTC string.
OUTBOX PAYLOAD RULE: `outbox_events.payload` stores the FULL event envelope,
not only the inner event-specific payload field. The RabbitMQ message body
must always contain `event_id`, `event_type`, `routing_key`, `artifact_id`,
`actor_id`, `actor_role`, `timestamp`, `correlation_id`, `reason`, and `payload`.
Chain of Custody consumer reads these top-level fields directly.

## 5. ID FORMAT
```
artifact_id      : UUID v4 (plain, no prefix in DB)
event_id         : UUID v4
report_id        : UUID v4
correlation_id   : UUID v4
ledger_record_id : UUID v4
```

## 6. JWT
```
Algorithm  : HS256
Secret     : loaded from JWT_SECRET env var (set in .env)
Expiry     : 30 days for demo tokens
```
Tokens generated once with `scripts/generate_demo_tokens.py`.
Nginx routes all external traffic. JWT validation is performed through Nginx
`auth_request` by calling `/internal/auth/validate` on the Evidence Collector.
Downstream services trust `X-User-Id`, `X-User-Role`, and `X-Correlation-Id`
headers forwarded by the gateway — they do not re-decode the JWT.

## 7. INGESTION FAILURE HANDLING
```
If Hash & Sign fails   → mark artifact INGESTION_FAILED, delete file, return 503.
If Ledger append fails → mark artifact INGESTION_FAILED, return 503.
If RabbitMQ publish fails → ingestion confirmed (hash+ledger succeeded).
                            Event stored in outbox_events, retried by outbox worker.
```

## 8. DUPLICATE ARTIFACT
Same file uploaded twice → allowed. New `artifact_id` generated each time.
No deduplication in MVP.

## 9. VERIFICATION FLOW
`POST /evidence/{artifactId}/verify` accepts a file upload (the file to check).
Evidence Collector saves it to the shared volume at:
`/evidence-storage/tmp/{artifact_id}/{verification_id}.bin`
(NOT to local /tmp — Hash & Sign must be able to read this path via shared volume.)

Full verification steps (in order):
1. Save uploaded file to `/evidence-storage/tmp/{artifact_id}/{verification_id}.bin`
2. Call Hash & Sign → `RecomputeHash(temp_file_path)` → `current_hash`
3. Call Ledger → `GetProofByArtifactId(artifact_id)` → `original_hash + signature_value`
4. Call Hash & Sign → `VerifySignature(original_hash, signature_value)` → `signature_valid`
5. Call Ledger → `ValidateLedgerChain()` → `ledger_chain_valid`
6. Compare `original_hash == current_hash` → VALID or TAMPERED
7. Append `VerificationRecord` to Ledger (`verification_result`, `original_hash`, `current_hash`)
8. Publish `VerificationPassed` or `VerificationFailed` event to RabbitMQ
9. Delete temp file from `/evidence-storage/tmp/`

Response includes: `artifact_id`, `verification_result`, `original_hash`, `current_hash`,
`signature_valid`, `ledger_chain_valid`, `verified_at`.

## 10. REPORT TRIGGER
`POST /reports/{artifactId}` triggers report generation.
Audit Reporter pulls from Evidence Collector, Ledger, Chain of Custody via REST.
Computes SHA-256 of the generated PDF bytes.
Stores report metadata + hash in `report_db`.
Publishes `ReportGenerated` event.
`ReportDownloaded` is published when `GET /reports/{reportId}/download` is called.
`ReportVerified` is published when `POST /reports/{reportId}/verify` is called.

## 11. AUDIT REPORTER → LEDGER COMMUNICATION
Audit Reporter calls Ledger via REST (`GET /ledger/artifacts/{artifactId}`).
No gRPC needed between Audit Reporter and Ledger.

## 12. DEMO PRE-FLIGHT (Port Lockdown)
Development: all service ports are open to host for debugging.
Before demo: in `docker-compose.yml`, comment out `ports:` on all internal
services and switch to `expose:` only. Only `gateway:8080` and
`rabbitmq:15672` (management UI) remain host-accessible.
RabbitMQ AMQP port 5672 must also be closed to host before demo.

## 13. CROSS-SERVICE HEADERS
All internal REST calls include:
```
X-Correlation-Id : forwarded from original request
X-User-Id        : forwarded from gateway
X-User-Role      : forwarded from gateway
```
