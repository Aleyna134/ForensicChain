import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# The implementation plan uses LEDGER_DB_URL
DATABASE_URL = os.getenv("LEDGER_DB_URL", "postgresql://forensic:forensic_pass@ledger-db:5432/ledger_db")

# In case it's run locally without the ledger-db hostname
if "ledger-db" in DATABASE_URL and os.getenv("ENV") == "local":
    DATABASE_URL = DATABASE_URL.replace("ledger-db", "localhost")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
