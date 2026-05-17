import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("EVIDENCE_DB_URL", "postgresql://forensic:forensic_pass@evidence-db:5432/evidence_db")

if "evidence-db" in DATABASE_URL and os.getenv("ENV") == "local":
    DATABASE_URL = DATABASE_URL.replace("evidence-db", "localhost")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
