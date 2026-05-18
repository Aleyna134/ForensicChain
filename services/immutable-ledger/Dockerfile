FROM python:3.11-slim

WORKDIR /app

# Install libpq-dev and gcc for psycopg2 compilation if needed (though psycopg2-binary usually avoids this, it's good practice for slim images)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
# We assume gRPC stubs have already been generated locally
COPY . .

# Ensure python path includes the current directory for absolute imports
ENV PYTHONPATH=/app

# The container entrypoint starts both the gRPC and FastAPI server via main.py
CMD ["python", "main.py"]
