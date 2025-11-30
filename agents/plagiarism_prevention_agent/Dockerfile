FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install lightweight system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY agents/plagiarism_prevention_agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agents/plagiarism_prevention_agent ./agents/plagiarism_prevention_agent

# Set Python path to allow absolute-style imports
ENV PYTHONPATH=/app/agents/plagiarism_prevention_agent

# Expose port
EXPOSE 8000

# Run FastAPI app
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
