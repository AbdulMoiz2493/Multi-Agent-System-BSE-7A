FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install agent-specific requirements
COPY agents/citation_manager/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code and shared modules
COPY agents/citation_manager ./agents/citation_manager
COPY shared ./shared

# Ensure CSL styles are available inside the container
ENV CSL_STYLE_DIR=/app/agents/citation_manager/csl

# Expose port and run uvicorn
EXPOSE 5016
CMD ["python", "-m", "uvicorn", "agents.citation_manager.app:app", "--host", "0.0.0.0", "--port", "5016"]
