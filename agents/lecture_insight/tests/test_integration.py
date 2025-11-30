"""
Integration Test for Lecture Insight Agent
Tests complete pipeline with REAL APIs - NO MOCK DATA
"""
import asyncio
import requests
import json
import time
from pathlib import Path


def test_lecture_insight_agent():
    """
    Comprehensive test of Lecture Insight Agent with real APIs.
    
    Tests:
    - Health endpoint
    - Agent info endpoint  
    - Complete lecture processing pipeline
    - All 5 nodes with real API calls (AssemblyAI, Gemini, Tavily, YouTube)
    - Output schema validation
    - Processing time measurement
    """
    
    BASE_URL = "http://localhost:5020"
    
    print("=" * 80)
    print("🧪 LECTURE INSIGHT AGENT - INTEGRATION TEST (REAL APIs)")
    print("=" * 80)
    
    # ========================================================================
    # TEST 1: Health Check
    # ========================================================================
    print("\n[1/4] Testing Health Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        health = response.json()
        assert health["status"] == "healthy", "Agent not healthy"
        print(f"   ✅ Health: {health['status']}")
        print(f"   ✅ Agent: {health['agent']}")
        print(f"   ✅ Version: {health['version']}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    # ========================================================================
    # TEST 2: Agent Info
    # ========================================================================
    print("\n[2/4] Testing Agent Info Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/agent-info", timeout=5)
        assert response.status_code == 200, f"Agent info failed: {response.status_code}"
        info = response.json()
        
        # Validate required fields
        assert info["agent_id"] == "lecture-insight-v1", "Wrong agent ID"
        assert info["endpoint"] == "/api/v1/process-lecture", "Wrong endpoint"
        assert "audio-transcription" in info["capabilities"], "Missing transcription capability"
        assert "mp3" in info["supported_formats"], "MP3 not supported"
        
        print(f"   ✅ Agent ID: {info['agent_id']}")
        print(f"   ✅ Endpoint: {info['endpoint']}")
        print(f"   ✅ Capabilities: {len(info['capabilities'])} features")
        print(f"   ✅ Formats: {', '.join(info['supported_formats'])}")
    except Exception as e:
        print(f"   ❌ Agent info failed: {e}")
        return False
    
    # ========================================================================
    # TEST 3: Complete Lecture Processing with REAL APIs
    # ========================================================================
    print("\n[3/4] Testing Lecture Processing (REAL APIs)...")
    print("   🎙️  Using real audio from GitHub")
    print("   🤖 Transcription: AssemblyAI API")
    print("   🧠 Summarization: Google Gemini 2.5 Flash")
    print("   🔍 Gap Analysis: Google Gemini 2.5 Flash")
    print("   📚 Article Search: Tavily API")
    print("   🎥 Video Search: YouTube Data API v3")
    print()
    
    request_payload = {
        "audio_input": {
            "type": "url",
            "data": "https://github.com/AssemblyAI-Community/audio-examples/raw/main/20230607_me_canadian_wildfires.mp3",
            "format": "mp3"
        },
        "user_id": "test-user-integration",
        "preferences": {
            "resource_limit": 8,
            "language": "en",
            "include_videos": True,
            "include_articles": True
        }
    }
    
    print("   📤 Sending request to /api/v1/process-lecture...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/process-lecture",
            json=request_payload,
            timeout=90  # Real APIs can take time
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code != 200:
            print(f"   ❌ Request failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
        
        result = response.json()
        
        print(f"\n   ✅ SUCCESS in {elapsed:.2f}s")
        print("   " + "=" * 76)
        
        # ====================================================================
        # Validate Output Schema (PRD Compliance)
        # ====================================================================
        print("\n   📋 OUTPUT SCHEMA VALIDATION:")
        
        required_fields = ["transcript", "summary", "keywords", "learning_gaps", "resources", "metadata"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
            print(f"   ✅ {field:20s} - Present")
        
        # Validate transcript
        transcript = result["transcript"]
        assert isinstance(transcript, str), "Transcript must be string"
        assert len(transcript) > 100, "Transcript too short"
        word_count = len(transcript.split())
        print(f"\n   📝 TRANSCRIPT:")
        print(f"      Words: {word_count}")
        print(f"      Preview: {transcript[:100]}...")
        
        # Validate summary
        summary = result["summary"]
        assert isinstance(summary, str), "Summary must be string"
        assert len(summary) > 50, "Summary too short"
        print(f"\n   📄 SUMMARY:")
        print(f"      Length: {len(summary)} characters")
        print(f"      Preview: {summary[:150]}...")
        
        # Validate keywords
        keywords = result["keywords"]
        assert isinstance(keywords, list), "Keywords must be list"
        assert len(keywords) >= 3, f"Expected ≥3 keywords, got {len(keywords)}"
        print(f"\n   🔑 KEYWORDS ({len(keywords)}):")
        for i, kw in enumerate(keywords[:5], 1):
            print(f"      {i}. {kw}")
        
        # Validate learning gaps
        gaps = result["learning_gaps"]
        assert isinstance(gaps, list), "Learning gaps must be list"
        assert len(gaps) >= 2, f"Expected ≥2 learning gaps, got {len(gaps)}"
        print(f"\n   🎯 LEARNING GAPS ({len(gaps)}):")
        for i, gap in enumerate(gaps[:5], 1):
            print(f"      {i}. {gap}")
        
        # Validate resources
        resources = result["resources"]
        assert "articles" in resources, "Missing articles in resources"
        assert "videos" in resources, "Missing videos in resources"
        
        articles = resources["articles"]
        videos = resources["videos"]
        
        print(f"\n   📚 RESOURCES:")
        print(f"      Articles: {len(articles)}")
        print(f"      Videos: {len(videos)}")
        print(f"      Total: {len(articles) + len(videos)}")
        
        # Validate article structure
        if articles:
            article = articles[0]
            required_article_fields = ["title", "url", "description", "source", "relevance_score"]
            for field in required_article_fields:
                assert field in article, f"Article missing field: {field}"
            
            print(f"\n      Sample Article:")
            print(f"      - Title: {article['title'][:60]}")
            print(f"      - URL: {article['url']}")
            print(f"      - Source: {article['source']}")
            print(f"      - Relevance: {article['relevance_score']:.2f}")
        else:
            print(f"      ⚠️  No articles found (Tavily might have returned no results)")
        
        # Validate video structure
        if videos:
            video = videos[0]
            required_video_fields = ["title", "url", "thumbnail", "channel", "duration", "source", "relevance_score"]
            for field in required_video_fields:
                assert field in video, f"Video missing field: {field}"
            
            print(f"\n      Sample Video:")
            print(f"      - Title: {video['title'][:60]}")
            print(f"      - Channel: {video['channel']}")
            print(f"      - Duration: {video['duration']}")
            print(f"      - Relevance: {video['relevance_score']:.2f}")
        else:
            print(f"      ⚠️  No videos found (YouTube might have returned no results)")
        
        # Validate metadata
        metadata = result["metadata"]
        required_metadata = ["processing_time_seconds", "audio_duration_seconds", "timestamp"]
        for field in required_metadata:
            assert field in metadata, f"Metadata missing field: {field}"
        
        print(f"\n   ⏱️  METADATA:")
        print(f"      Processing Time: {metadata['processing_time_seconds']:.2f}s")
        print(f"      Audio Duration: {metadata['audio_duration_seconds']:.2f}s")
        print(f"      Timestamp: {metadata['timestamp']}")
        
        # ====================================================================
        # Validate Real API Usage (No Mock Data)
        # ====================================================================
        print(f"\n   🔍 REAL API VALIDATION:")
        
        # Check that we got real transcription
        assert "canadian" in transcript.lower() or "wildfire" in transcript.lower(), \
            "Transcript doesn't match audio content - might be mock data!"
        print(f"   ✅ Transcription contains expected content (AssemblyAI)")
        
        # Check that keywords are relevant
        keyword_str = " ".join(keywords).lower()
        assert any(word in keyword_str for word in ["fire", "smoke", "air", "quality", "canada"]), \
            "Keywords don't match audio topic - might be mock data!"
        print(f"   ✅ Keywords are relevant to audio content")
        
        # Check that resources exist
        total_resources = len(articles) + len(videos)
        assert total_resources > 0, "No resources found - APIs might not be working!"
        print(f"   ✅ Resources found from real APIs ({total_resources} total)")
        
        # ====================================================================
        # Save Results
        # ====================================================================
        output_file = "agents/lecture_insight/tests/integration_test_results.json"
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n   💾 Full results saved to: {output_file}")
        
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout (processing took >{90}s)")
        return False
    except AssertionError as e:
        print(f"   ❌ Validation failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================================================
    # TEST 4: Final Validation
    # ========================================================================
    print("\n[4/4] Final Validation...")
    
    checks = [
        (word_count > 100, f"Transcript word count > 100: {word_count}"),
        (len(keywords) >= 3, f"Keywords >= 3: {len(keywords)}"),
        (len(gaps) >= 2, f"Learning gaps >= 2: {len(gaps)}"),
        (total_resources > 0, f"Resources found: {total_resources}"),
        (len(summary) > 50, f"Summary length > 50: {len(summary)}"),
    ]
    
    passed = sum(1 for check, _ in checks if check)
    
    print()
    for check, message in checks:
        status = "✅" if check else "❌"
        print(f"   {status} {message}")
    
    print("\n" + "=" * 80)
    if passed == len(checks):
        print(f"🏆 ALL TESTS PASSED ({passed}/{len(checks)})")
        print("✅ All APIs working correctly (AssemblyAI, Gemini, Tavily, YouTube)")
        print("✅ No mock data detected")
        print("✅ Output schema PRD-compliant")
        print("=" * 80)
        return True
    else:
        print(f"⚠️  PARTIAL PASS ({passed}/{len(checks)} checks)")
        print("=" * 80)
        return False


if __name__ == "__main__":
    print("\n⚠️  PREREQUISITES:")
    print("   1. Start server: python -m uvicorn agents.lecture_insight.app:app --host 0.0.0.0 --port 5020")
    print("   2. Ensure .env file has API keys:")
    print("      - ASSEMBLYAI_API_KEY")
    print("      - GEMINI_API_KEY")
    print("      - TAVILY_API_KEY")
    print("      - YOUTUBE_API_KEY")
    print()
    
    input("Press Enter to start test...")
    
    success = test_lecture_insight_agent()
    exit(0 if success else 1)
