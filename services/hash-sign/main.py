import asyncio
import logging
import grpc
from fastapi import FastAPI
import uvicorn
import hash_sign_pb2_grpc
from servicer import HashSignServicer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI Setup ---
app = FastAPI(title="Hash & Sign Service")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "hash-sign"}

# --- gRPC Server Setup ---
async def serve_grpc():
    server = grpc.aio.server()
    hash_sign_pb2_grpc.add_HashSignServiceServicer_to_server(HashSignServicer(), server)
    server.add_insecure_port("[::]:50051")
    logger.info("Starting gRPC server on port 50051...")
    await server.start()
    await server.wait_for_termination()

# --- Main Entry Point ---
async def main():
    # Start the gRPC server as a background task
    grpc_task = asyncio.create_task(serve_grpc())
    
    # Run the FastAPI server using uvicorn config
    # We run it on port 8002 to avoid conflicts, and since the docker-compose doesn't map it for host
    # it only exposes 50051 for grpc. The health check is typically used internally by docker.
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8002, log_level="info")
    server = uvicorn.Server(config)
    
    logger.info("Starting FastAPI server on port 8002...")
    # Serve FastAPI
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
