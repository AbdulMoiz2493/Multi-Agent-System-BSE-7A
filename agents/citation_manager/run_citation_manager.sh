#!/bin/bash
uvicorn agents.citation_manager.app:app --host 127.0.0.1 --port 5016 --reload


# Health check
# http://127.0.0.1:5016/health
# http://127.0.0.1:5016/csl_status