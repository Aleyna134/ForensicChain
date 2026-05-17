from fastapi import FastAPI
import uvicorn
from routers import evidence
from db.database import engine, Base

# Create the initial tables based on SQLAlchemy models
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ForensicChain - Evidence Collector")

# Include the evidence routes
app.include_router(evidence.router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "evidence-collector"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
