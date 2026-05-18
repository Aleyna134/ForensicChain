# services/hash-sign/main.py
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "service": "hash-sign"}
