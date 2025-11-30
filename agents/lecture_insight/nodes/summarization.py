"""
Summarization Node - Generates intelligent summaries using Google Gemini

Production-ready implementation with:
- Structured JSON output (title, summary, key_points, main_concepts)
- Educational content optimization
- Retry logic with exponential backoff
- Quality validation and error handling
- Token usage tracking
"""

import logging
import os
import asyncio
import json
from typing import Dict, Any, List, Tuple

_logger = logging.getLogger(__name__)


async def summarize_content(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate comprehensive summary from transcript using Google Gemini.
    
    Produces structured educational summary including:
    - Title: Concise lecture title
    - Summary: 3-4 sentence overview of main content
    - Key Points: List of main takeaways
    - Main Concepts: Core technical terms and ideas
    
    Args:
        state: Current workflow state with:
            - transcript: Full lecture transcript text
            - audio_duration: Optional duration for context
        
    Returns:
        Updated state with:
            - summary: Structured summary dict with title, summary, key_points, main_concepts
            - keywords: List of extracted keywords (for backward compatibility)
            - error: Error message if summarization failed
    
    Example:
        >>> state = {"transcript": "Welcome to Python basics..."}
        >>> result = await summarize_content(state)
        >>> print(result["summary"]["title"])
        "Introduction to Python Programming"
    """
    _logger.info("📝 Starting content summarization with Gemini...")
    
    try:
        transcript = state.get("transcript", "")
        
        if not transcript:
            raise ValueError("No transcript available for summarization")
        
        if len(transcript.strip()) < 50:
            raise ValueError(f"Transcript too short for meaningful summary: {len(transcript)} chars")
        
        # Generate summary using Gemini with retry logic
        summary_dict, keywords = await _summarize_with_gemini(transcript)
        
        state["summary"] = summary_dict
        state["keywords"] = keywords
        
        _logger.info(
            f"✅ Summarization complete: '{summary_dict['title']}' - "
            f"{len(keywords)} keywords, {len(summary_dict['key_points'])} key points"
        )
        return state
        
    except Exception as e:
        _logger.error(f"❌ Summarization failed: {type(e).__name__}: {e}")
        state["error"] = f"Summarization error: {str(e)}"
        state["summary"] = {
            "title": "Summary Unavailable",
            "summary": "",
            "key_points": [],
            "main_concepts": []
        }
        state["keywords"] = []
        return state


async def _summarize_with_gemini(transcript: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Generate structured summary using Google Gemini API with retry logic.
    
    Uses Gemini 1.5 Flash with optimized prompts for educational content.
    Returns structured JSON with title, summary, key_points, and main_concepts.
    
    Features:
    - Retry logic (3 attempts with exponential backoff)
    - JSON output validation
    - Educational content optimization
    - Token-efficient prompting
    - Quality validation (no empty responses)
    
    Args:
        transcript: Full lecture transcript text
    
    Returns:
        Tuple of (summary_dict, keywords_list) where:
        - summary_dict: {"title": str, "summary": str, "key_points": list, "main_concepts": list}
        - keywords_list: List of key technical terms
    
    Raises:
        ValueError: If API key not set or transcript invalid
        Exception: If summarization fails after all retries
    
    Requires:
        GEMINI_API_KEY environment variable
    """
    max_retries = 3
    retry_delay = 2  # seconds
    
    try:
        # Get API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set GEMINI_API_KEY environment variable."
            )
        
        for attempt in range(max_retries):
            try:
                import google.generativeai as genai
                
                if attempt > 0:
                    _logger.info(f"🔄 Retry attempt {attempt + 1}/{max_retries}")
                
                _logger.info("🤖 Generating summary with Gemini 2.5 Flash...")
                
                # Configure Gemini
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # Optimized prompt for educational content with JSON output
                prompt = f"""You are an expert educational content analyzer. Analyze this lecture transcript and provide a structured summary.

TRANSCRIPT:
{transcript}

Generate a JSON response with this EXACT structure (no markdown, just raw JSON):
{{
  "title": "A concise, descriptive title for this lecture (max 10 words)",
  "summary": "A clear 3-4 sentence summary of the main content and learning objectives",
  "key_points": [
    "First major point or takeaway",
    "Second major point or takeaway",
    "Third major point or takeaway"
  ],
  "main_concepts": [
    "Core concept 1",
    "Core concept 2",
    "Core concept 3",
    "Core concept 4",
    "Core concept 5"
  ]
}}

Focus on:
- Educational value and learning objectives
- Technical accuracy
- Key concepts students should understand
- Practical applications mentioned

Return ONLY the JSON object, no other text."""

                # Generate summary (blocking call, run in executor)
                start_time = asyncio.get_event_loop().time()
                
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    model.generate_content,
                    prompt
                )
                
                elapsed_time = asyncio.get_event_loop().time() - start_time
                _logger.info(f"⏱️ Gemini response received in {elapsed_time:.1f}s")
                
                # Extract and parse JSON response
                response_text = response.text.strip()
                
                # Clean up markdown code blocks if present
                if response_text.startswith("```json"):
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif response_text.startswith("```"):
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                # Parse JSON
                try:
                    summary_dict = json.loads(response_text)
                except json.JSONDecodeError as je:
                    _logger.warning(f"⚠️ JSON parse error: {je}. Response: {response_text[:200]}")
                    raise ValueError(f"Invalid JSON response from Gemini: {je}")
                
                # Validate structure
                required_keys = {"title", "summary", "key_points", "main_concepts"}
                if not all(key in summary_dict for key in required_keys):
                    missing = required_keys - set(summary_dict.keys())
                    raise ValueError(f"Missing required keys in Gemini response: {missing}")
                
                # Validate content quality (not empty)
                if not summary_dict["title"] or len(summary_dict["title"].strip()) < 5:
                    raise ValueError("Gemini returned empty or invalid title")
                
                if not summary_dict["summary"] or len(summary_dict["summary"].strip()) < 20:
                    raise ValueError("Gemini returned empty or invalid summary")
                
                if not summary_dict["key_points"] or len(summary_dict["key_points"]) < 2:
                    raise ValueError("Gemini returned insufficient key points")
                
                # Extract keywords from main_concepts
                keywords = summary_dict["main_concepts"][:10]  # Limit to 10 keywords
                
                _logger.info(
                    f"✅ Summary generated: {len(summary_dict['key_points'])} points, "
                    f"{len(keywords)} keywords"
                )
                
                return summary_dict, keywords
                
            except ImportError:
                _logger.error("❌ Google Generative AI SDK not installed")
                raise ValueError(
                    "Google Generative AI SDK not installed. Install with: pip install google-generativeai"
                )
                
            except (ConnectionError, TimeoutError, OSError) as e:
                # Network-related errors - retry with exponential backoff
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    _logger.warning(f"⚠️ Network error: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    _logger.error(f"❌ Summarization failed after {max_retries} attempts: {e}")
                    raise
                    
            except ValueError as ve:
                # Validation errors - retry (might be transient API issue)
                if attempt < max_retries - 1 and "JSON" in str(ve):
                    wait_time = retry_delay * (2 ** attempt)
                    _logger.warning(f"⚠️ Validation error: {ve}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise
                    
            except Exception as e:
                # Other errors - log and retry
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    _logger.warning(
                        f"⚠️ Gemini error: {type(e).__name__}: {e}. Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    _logger.error(f"❌ Gemini summarization failed: {type(e).__name__}: {e}")
                    raise
        
        # Should never reach here
        raise Exception(f"Summarization failed after {max_retries} retry attempts")
        
    except Exception as e:
        _logger.error(f"❌ Fatal error in Gemini summarization: {e}")
        raise
