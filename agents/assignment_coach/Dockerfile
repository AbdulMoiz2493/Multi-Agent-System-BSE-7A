FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy local requirements (lightweight)
COPY agents/assignment_coach/requirements.txt ./requirements.txt

# Pre-install CPU-only ONNX runtime before ChromaDB to avoid heavy GPU version
RUN pip install --no-cache-dir onnxruntime

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agents/assignment_coach ./agents/assignment_coach
COPY shared ./shared

# Set Python path to find shared modules
ENV PYTHONPATH=/app

EXPOSE 5012

CMD ["uvicorn", "agents.assignment_coach.app:app", "--host", "0.0.0.0", "--port", "5012"]
