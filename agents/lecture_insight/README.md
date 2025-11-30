# Lecture Insight Agent

AI-powered agent that processes audio lectures to generate transcripts, summaries, identifies learning gaps, and provides curated educational resources.

## Description

The Lecture Insight Agent transforms audio lectures into comprehensive learning materials by:
- Transcribing audio using AssemblyAI
- Generating structured summaries with Google Gemini
- Identifying prerequisite knowledge gaps
- Searching for relevant articles (Tavily) and videos (YouTube)

## Input Format

```json
{
  "audio_input": {
    "type": "base64",
    "data": "<base64-encoded-audio-data>",
    "format": "mp3"
  },
  "user_id": "user-123",
  "preferences": {
    "resource_limit": 10,
    "language": "en",
    "include_videos": true,
    "include_articles": true
  }
}
```

### Audio Input Types
- `base64`: Base64-encoded audio string
- `url`: Direct URL to audio file
- `stream`: Audio stream 

### Supported Formats
- `mp3`
- `wav`
- `m4a`

## Output Format

```json
{
  "transcript": "Full transcription text...",
  "summary": "Formatted summary with title, overview, key points...",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "learning_gaps": ["prerequisite1", "prerequisite2"],
  "resources": {
    "articles": [
      {
        "title": "Article Title",
        "url": "https://...",
        "description": "Article description",
        "source": "web_search",
        "relevance_score": 0.95
      }
    ],
    "videos": [
      {
        "title": "Video Title",
        "url": "https://youtube.com/...",
        "thumbnail": "https://...",
        "channel": "Channel Name",
        "duration": "10:30",
        "source": "video_platform",
        "relevance_score": 0.92
      }
    ]
  },
  "metadata": {
    "processing_time_seconds": 35.2,
    "audio_duration_seconds": 120.5,
    "timestamp": "2025-11-15T10:30:00"
  }
}
```

## Running the Server

### Prerequisites

1. **Install Dependencies**
```bash
cd agents/lecture_insight
pip install -r requirements.txt
```

2. **Configure API Keys**

Create a `.env` file in the project root:
```env
ASSEMBLYAI_API_KEY=your_assemblyai_key
GEMINI_API_KEY=your_gemini_key
TAVILY_API_KEY=your_tavily_key
YOUTUBE_API_KEY=your_youtube_key
```

3. **Start the Server**
```bash
python -m uvicorn agents.lecture_insight.app:app --host 0.0.0.0 --port 5020
```

Server will be available at `http://localhost:5020`

### Available Endpoints

- `GET /api/v1/health` - Health check
- `GET /api/v1/agent-info` - Agent capabilities
- `POST /api/v1/process-lecture` - Process lecture audio

## Running the Test

### Run Integration Test

```bash
python agents/lecture_insight/tests/test_integration.py
```

**Test validates:**
- ✅ All endpoints working
- ✅ Real API integration (AssemblyAI, Gemini, Tavily, YouTube)
- ✅ Output schema compliance
- ✅ No mock data

Test results saved to: `agents/lecture_insight/tests/integration_test_results.json`

## Integration with Supervisor

### Step 1: Convert Audio to Base64

The supervisor must convert audio files to base64 before sending to this agent.

**Python Example:**
```python
import base64

def convert_audio_to_base64(file_path: str) -> str:
    """Convert audio file to base64 string."""
    with open(file_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
        base64_string = base64.b64encode(audio_bytes).decode('utf-8')
    return base64_string

# Usage
audio_base64 = convert_audio_to_base64("lecture.mp3")
```

### Step 2: Send Request to Agent

**Request:**
```python
import requests

payload = {
    "audio_input": {
        "type": "base64",
        "data": audio_base64,  # Base64 string from Step 1
        "format": "mp3"
    },
    "user_id": "supervisor-user-001",
    "preferences": {
        "resource_limit": 8,
        "language": "en",
        "include_videos": True,
        "include_articles": True
    }
}

response = requests.post(
    "http://localhost:5020/api/v1/process-lecture",
    json=payload,
    timeout=90
)

result = response.json()
```

### Step 3: Handle Response

**Success Response (200):**
```python
{
    "transcript": "...",
    "summary": "...",
    "keywords": [...],
    "learning_gaps": [...],
    "resources": {...},
    "metadata": {...}
}
```

**Error Response (400/500):**
```python
{
    "error": "Error message",
    "detail": "Detailed error information"
}
```

### Alternative: URL-based Input

If audio is already hosted, use URL input instead:

```python
payload = {
    "audio_input": {
        "type": "url",
        "data": "https://example.com/lecture.mp3",
        "format": "mp3"
    },
    "user_id": "supervisor-user-001"
}
```

### Integration Notes

1. **Base64 is Required for Local Files**: If the supervisor has local audio files, they must be converted to base64
2. **URL Input for Remote Files**: If audio is already hosted online, use URL input for better performance
3. **Timeout Handling**: Processing can take 30-60 seconds, set appropriate timeouts
4. **LTM Caching**: Identical audio inputs are cached automatically based on content hash
5. **Error Handling**: Check `response.status_code` and handle errors appropriately

### Example Supervisor Integration

```python
class SupervisorAgent:
    def process_lecture_task(self, audio_file_path: str, user_id: str):
        """Process lecture using Lecture Insight Agent."""
        
        # Step 1: Convert to base64
        with open(audio_file_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Step 2: Prepare request
        payload = {
            "audio_input": {
                "type": "base64",
                "data": audio_base64,
                "format": "mp3"
            },
            "user_id": user_id,
            "preferences": {
                "resource_limit": 10,
                "include_videos": True,
                "include_articles": True
            }
        }
        
        # Step 3: Send to agent
        try:
            response = requests.post(
                "http://localhost:5020/api/v1/process-lecture",
                json=payload,
                timeout=90
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            return {"error": "Agent timeout"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Agent error: {str(e)}"}
```

---

**Agent Version:** 1.0.0  
**Endpoint:** `/api/v1/process-lecture`  
**Port:** 5020
