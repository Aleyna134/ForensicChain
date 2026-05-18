# RabbitMQ Topology

## Exchange & Queue Layout

```
Exchange:  forensicchain.events   (type: topic, durable: true)
Queue:     custody.events.queue   (durable: true)
Binding:   forensicchain.#  →  custody.events.queue

DLX:       forensicchain.dlx      (type: direct, durable: true)
DLQ:       custody.events.dlq     (durable: true)
Binding:   custody.events.dlq  →  custody.events.dlq  (via DLX)
```

## Routing Keys

| Event                 | Routing Key                            |
|-----------------------|----------------------------------------|
| EvidenceIngested      | `forensicchain.evidence.ingested`      |
| EvidenceViewed        | `forensicchain.evidence.viewed`        |
| EvidenceDownloaded    | `forensicchain.evidence.downloaded`    |
| VerificationRequested | `forensicchain.verification.requested` |
| VerificationPassed    | `forensicchain.verification.passed`    |
| VerificationFailed    | `forensicchain.verification.failed`    |
| ReportGenerated       | `forensicchain.report.generated`       |
| ReportDownloaded      | `forensicchain.report.downloaded`      |
| ReportVerified        | `forensicchain.report.verified`        |

## Publisher Ownership

| Publisher                | Events Published                                              |
|--------------------------|---------------------------------------------------------------|
| Evidence Collector       | `forensicchain.evidence.*`, `forensicchain.verification.*`    |
| Audit Reporter           | `forensicchain.report.*`                                      |

## Retry Strategy

- Consumer tracks `x-retry-count` message header (starts at 0).
- On processing failure:
  - If `retry_count < 3`: publish a retry copy to `forensicchain.events` with `x-retry-count + 1`, then **ack** the original.
  - If `retry_count >= 3`: **reject** with `requeue=False` → RabbitMQ routes to DLX → DLQ.
- Total attempts before DLQ: **4** (1 initial + 3 retries).
- No `x-message-ttl` on the queue — TTL is not a retry mechanism here.

## Connection Details (development)

| Resource              | Host (dev)               | Notes                          |
|-----------------------|--------------------------|--------------------------------|
| AMQP                  | `localhost:5672`         | Close to host before demo      |
| Management UI         | `http://localhost:15672` | guest / guest                  |
| Internal (container)  | `rabbitmq:5672`          | Always reachable via Docker net |
