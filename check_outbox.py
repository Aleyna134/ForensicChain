import psycopg2
import json

conn = psycopg2.connect('postgresql://forensic:forensic_pass@localhost:5433/evidence_db')
cur = conn.cursor()
cur.execute("SELECT event_id, event_type, status, payload_json FROM outbox_events")
rows = cur.fetchall()
print(f"Total Outbox Events: {len(rows)}")
for r in rows:
    print(r[0], r[1], r[2])
    print(json.dumps(r[3], indent=2))
