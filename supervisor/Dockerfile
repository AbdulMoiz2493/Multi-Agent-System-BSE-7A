# Dockerfile for the Supervisor
FROM python:3.11-slim

WORKDIR /app

# Ensure output is unbuffered
ENV PYTHONUNBUFFERED=1

# Copy dependency manifest and install first to leverage build cache
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir python-multipart

# Copy application code
COPY . .

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "supervisor.main:app", "--host", "0.0.0.0", "--port", "8000"]
