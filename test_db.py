import psycopg2
import json

conn = psycopg2.connect("postgresql://user:password@localhost:5432/evidence_db")
cur = conn.cursor()
cur.execute("SELECT payload_json FROM outbox_events ORDER BY created_at DESC LIMIT 1;")
payload = cur.fetchone()[0]
print(json.dumps(payload, indent=2))
