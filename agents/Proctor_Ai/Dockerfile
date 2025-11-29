FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY agents/Proctor_Ai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code from the Proctor_Ai folder
COPY agents/Proctor_Ai/app ./app
COPY agents/Proctor_Ai/alembic ./alembic
COPY agents/Proctor_Ai/alembic.ini ./alembic.ini

# Expose port
EXPOSE 8080

# Start command - tables auto-create on startup via SQLAlchemy
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

