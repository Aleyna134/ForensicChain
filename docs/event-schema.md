# Event Schema

All RabbitMQ messages share a common JSON envelope. The `payload` field
carries event-specific data and varies by `event_type`.

## Envelope

```json
{
  "event_id":       "550e8400-e29b-41d4-a716-446655440000",
  "event_type":     "EvidenceIngested",
  "routing_key":    "forensicchain.evidence.ingested",
  "artifact_id":    "7d5f3c1a-2b4e-4f8a-9c6d-1e3f5a7b9c2d",
  "case_id":        "CASE-2026-001",
  "actor_id":       "user-analyst",
  "actor_role":     "ForensicAnalyst",
  "timestamp":      "2026-05-14T10:30:00Z",
  "correlation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "reason":         "Initial evidence ingestion",
  "payload":        {}
}
```

> **Outbox rule:** `outbox_events.payload` stores the **full envelope** above,
> not only the inner `payload` field. The RabbitMQ message body must always
> contain all top-level fields so the Chain of Custody consumer can read
> `event_id`, `event_type`, `artifact_id`, etc. directly from the message body.

## ID Formats

| Field            | Format  |
|------------------|---------|
| `event_id`       | UUID v4 |
| `artifact_id`    | UUID v4 |
| `correlation_id` | UUID v4 |
| `report_id`      | UUID v4 |

## Payloads by Event Type

### EvidenceIngested

```json
{
  "file_name":        "phone_extraction.zip",
  "file_size":        10485760,
  "artifact_type":    "MobileExtraction",
  "hash_algorithm":   "SHA-256",
  "hash_value":       "a3f5...c9d1",
  "ledger_record_id": "uuid"
}
```

### VerificationPassed

```json
{
  "verification_result": "VALID",
  "original_hash":       "a3f5...c9d1",
  "current_hash":        "a3f5...c9d1",
  "ledger_record_id":    "uuid"
}
```

### VerificationFailed

```json
{
  "verification_result": "TAMPERED",
  "original_hash":       "a3f5...c9d1",
  "current_hash":        "b7e2...f4a8"
}
```

### ReportGenerated

```json
{
  "report_id":     "uuid",
  "report_hash":   "sha256_of_report_bytes",
  "report_format": "PDF"
}
```

### EvidenceViewed / EvidenceDownloaded / ReportDownloaded

```json
{
  "ip_address": "192.168.1.10"
}
```
