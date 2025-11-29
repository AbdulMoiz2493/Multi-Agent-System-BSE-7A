# Multi-Agent System Setup Guide

## Prerequisites

- Python 3.8 or higher
- PowerShell (Windows) or Bash (Linux/Mac)
- Gemini API Key from Google AI Studio

## Initial Setup

### 1. Create Python Virtual Environment

```powershell
# Navigate to project directory
cd c:\Code\SPM-Project\Multi-Agent-System-BSE-7A

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate
```

For Linux/Mac:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```powershell
# Install supervisor dependencies
pip install -r requirements.txt

# Install assignment coach dependencies
pip install -r agents/assignment_coach/requirements.txt
```

### 3. Configure Gemini API Key

Create a `.env` file in the project root directory:

```powershell
# Create .env file
New-Item -Path .env -ItemType File -Force
```

Add your Gemini API key to the `.env` file:

```
GEMINI_API_KEY=your_api_key_here
```

**Important:** Replace `your_api_key_here` with your actual Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

The `.env` file should look like this:

```
GEMINI_API_KEY=AIzaSyCA5LS4JosheBjxJPBmU1uI2U0BqT7mf4I
```

⚠️ **Note:** Without a valid Gemini API key, the Assignment Coach will return generic responses instead of AI-powered, assignment-specific guidance.

## Running the System

### Start the Supervisor (Terminal 1)

```powershell
# Activate virtual environment if not already activated
.\venv\Scripts\activate

# Run supervisor on port 8000
uvicorn supervisor.main:app --host 0.0.0.0 --port 8000 --reload
```

The supervisor will be available at: `http://localhost:8000`

### Start the Assignment Coach Agent (Terminal 2)

```powershell
# Open a new terminal
cd c:\Code\SPM-Project\Multi-Agent-System-BSE-7A

# Activate virtual environment
.\venv\Scripts\activate

# Run assignment coach on port 5011
uvicorn agents.assignment_coach.app:app --host 0.0.0.0 --port 5011 --reload
```

The assignment coach will be available at: `http://localhost:5011`

### Alternative: Using Bash Scripts (Linux/Mac)

```bash
# Start supervisor
./run_supervisor.sh

# Start assignment coach (in another terminal)
./run_assignment_coach.sh
```

## Verify Setup

### Check Supervisor Health

```powershell
curl http://localhost:8000/health
```

Expected response:

```json
{ "status": "healthy" }
```

### Check Assignment Coach Health

```powershell
curl http://localhost:5011/health
```

Expected response:

```json
{ "status": "healthy", "agent": "assignment_coach" }
```

### Test Assignment Coach with Gemini API

```powershell
# Run comprehensive test suite
powershell -ExecutionPolicy Bypass -File test_all_assignments_formatted.ps1
```

This will test 6 different assignments and show:

- Assignment summaries
- Task breakdowns
- Resource recommendations
- Student feedback
- Execution time and cache status

**Expected Output:** You should see detailed, assignment-specific responses with `Cached: False` and execution times of 8,000-12,000ms for fresh Gemini responses.

## Troubleshooting

### Generic Responses Issue

If you're getting generic responses like "Research and gather relevant materials":

1. **Verify API key is loaded:**

   ```powershell
   # Check .env file exists
   Get-Content .env
   ```

2. **Restart the Assignment Coach:**

   ```powershell
   # Stop the running process (Ctrl+C in the terminal)
   # Then restart:
   uvicorn agents.assignment_coach.app:app --host 0.0.0.0 --port 5011 --reload
   ```

3. **Clear cache and restart:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File restart_and_test.ps1
   ```

### Port Already in Use

If you see "Address already in use" error:

```powershell
# Find and kill process using port 8000 (supervisor)
Get-Process -Name python | Where-Object {$_.Path -like "*venv*"} | Stop-Process -Force

# Or for specific port
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

### API Key Not Loading

1. Verify `.env` file is in the project root (same directory as `main.py`)
2. Ensure there are no quotes around the API key
3. Check file encoding is UTF-8
4. Restart the agent after modifying `.env`

### Module Not Found Errors

```powershell
# Ensure virtual environment is activated
.\venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
pip install -r agents/assignment_coach/requirements.txt
```

## Testing Different Assignments

Use the test suite to verify functionality:

```powershell
# Test all 6 assignments with formatted output
powershell -ExecutionPolicy Bypass -File test_all_assignments_formatted.ps1
```

Test cases include:

1. E-commerce Database Schema (Advanced)
2. Python Calculator (Beginner)
3. ML Churn Prediction (Intermediate)
4. Web Portfolio (Intermediate)
5. Cybersecurity Audit (Advanced)
6. Mobile App Design (Beginner)

## Project Structure

```
Multi-Agent-System-BSE-7A/
├── .env                          # Gemini API key (create this)
├── venv/                         # Virtual environment (create this)
├── requirements.txt              # Supervisor dependencies
├── supervisor/
│   └── main.py                   # Supervisor FastAPI app
├── agents/
│   └── assignment_coach/
│       ├── app.py                # Assignment Coach FastAPI app
│       ├── coach_agent.py        # Core agent logic with Gemini
│       └── requirements.txt      # Agent dependencies
└── tests/
    └── test_all_assignments_formatted.ps1
```

## API Endpoints

### Supervisor (Port 8000)

- `GET /health` - Health check
- `POST /process` - Route requests to agents

### Assignment Coach (Port 5011)

- `GET /health` - Health check
- `POST /process` - Process assignment guidance requests
- `GET /capabilities` - Get agent capabilities

## Expected Behavior

With proper Gemini API configuration, the Assignment Coach should:

- Generate **detailed, context-aware summaries** of assignments
- Create **specific task breakdowns** with estimated durations
- Recommend **relevant resources** (articles, documentation, tutorials)
- Provide **personalized feedback** based on assignment difficulty and student level

**Without Gemini API key:** Responses will be generic placeholders.

## Support

For issues or questions, refer to the main `README.md` or check the test results for diagnostic information.
