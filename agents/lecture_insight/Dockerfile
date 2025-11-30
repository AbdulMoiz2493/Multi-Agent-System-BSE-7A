FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install agent-specific requirements
COPY agents/lecture_insight/requirements.txt /app/agents/lecture_insight/requirements.txt
RUN pip install --no-cache-dir -r /app/agents/lecture_insight/requirements.txt

# Copy shared modules and agent code
COPY shared/ /app/shared/
COPY agents/lecture_insight/ /app/agents/lecture_insight/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5020

# Run the agent
CMD ["python", "-m", "uvicorn", "agents.lecture_insight.app:app", "--host", "0.0.0.0", "--port", "5020"]
