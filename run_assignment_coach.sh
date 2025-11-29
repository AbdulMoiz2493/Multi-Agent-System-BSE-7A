#!/bin/bash
# run_assignment_coach.sh
echo "Starting Assignment Coach Agent..."
uvicorn agents.assignment_coach.app:app --host 0.0.0.0 --port 5011 --reload
