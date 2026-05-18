import psycopg2

conn = psycopg2.connect('postgresql://forensic:forensic_pass@localhost:5433/evidence_db')
conn.autocommit = True
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE outbox_events ADD COLUMN retry_count BIGINT NOT NULL DEFAULT 0;")
except psycopg2.errors.DuplicateColumn:
    pass

try:
    cur.execute("ALTER TABLE outbox_events ADD COLUMN next_retry_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();")
except psycopg2.errors.DuplicateColumn:
    pass

try:
    cur.execute("ALTER TABLE outbox_events ADD COLUMN last_error TEXT;")
except psycopg2.errors.DuplicateColumn:
    pass

print("Migration completed.")
