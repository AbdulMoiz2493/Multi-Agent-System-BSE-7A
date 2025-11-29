FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install agent-specific dependencies (from agent's own requirements.txt)
COPY agents/adaptive_quiz_master/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code and shared modules
COPY agents/adaptive_quiz_master ./agents/adaptive_quiz_master
COPY shared ./shared
COPY config/settings.yaml ./config/settings.yaml

# Run the agent
CMD ["python", "-m", "uvicorn", "agents.adaptive_quiz_master.app:app", "--host", "0.0.0.0", "--port", "5020"]