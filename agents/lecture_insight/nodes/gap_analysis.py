"""
Gap Analysis Node - Identifies learning prerequisites using Google Gemini

Production-ready implementation with:
- Pedagogical gap detection optimized for educational content
- Search query generation for resource discovery
- Retry logic with exponential backoff
- Quality validation and error handling
- Smart fallback for edge cases
"""

import logging
import os
import asyncio
import json
from typing import Dict, Any, List, Tuple

_logger = logging.getLogger(__name__)


async def analyze_gaps(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify learning prerequisites and generate search queries using Google Gemini.
    
    Analyzes the lecture content to determine what background knowledge students
    need, then generates targeted search queries to find supplementary resources.
    
    Produces:
    - Learning Gaps: List of prerequisite concepts/skills needed
    - Search Queries: Optimized queries for finding learning resources
    
    Args:
        state: Current workflow state with:
            - transcript: Full lecture transcript
            - summary: Structured summary dict (optional, improves accuracy)
            - keywords: List of key terms (optional)
        
    Returns:
        Updated state with:
            - learning_gaps: List of prerequisite knowledge areas
            - search_queries: List of search queries for resource discovery
            - error: Error message if gap analysis failed
    
    Example:
        >>> state = {
        ...     "transcript": "Today we'll cover neural networks...",
        ...     "summary": {"title": "Introduction to Neural Networks", ...}
        ... }
        >>> result = await analyze_gaps(state)
        >>> print(result["learning_gaps"])
        ["Linear algebra basics", "Calculus fundamentals", ...]
    """
    _logger.info("🔍 Analyzing learning gaps with Gemini...")
    
    try:
        transcript = state.get("transcript", "")
        summary = state.get("summary", {})
        keywords = state.get("keywords", [])
        
        if not transcript:
            raise ValueError("No transcript available for gap analysis")
        
        if len(transcript.strip()) < 50:
            raise ValueError(f"Transcript too short for gap analysis: {len(transcript)} chars")
        
        # Analyze gaps and generate search queries using Gemini
        learning_gaps, search_queries = await _analyze_with_gemini(
            transcript=transcript,
            summary=summary,
            keywords=keywords
        )
        
        state["learning_gaps"] = learning_gaps
        state["search_queries"] = search_queries
        
        _logger.info(
            f"✅ Gap analysis complete: {len(learning_gaps)} gaps identified, "
            f"{len(search_queries)} search queries generated"
        )
        return state
        
    except Exception as e:
        _logger.error(f"❌ Gap analysis failed: {type(e).__name__}: {e}")
        state["error"] = f"Gap analysis error: {str(e)}"
        state["learning_gaps"] = []
        state["search_queries"] = []
        return state


async def _analyze_with_gemini(
    transcript: str,
    summary: Dict[str, Any],
    keywords: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Analyze learning gaps and generate search queries using Google Gemini.
    
    Uses Gemini 1.5 Flash with pedagogical prompts to identify prerequisite
    knowledge and generate targeted search queries for resource discovery.
    
    Features:
    - Retry logic (3 attempts with exponential backoff)
    - JSON output validation
    - Educational gap detection (not generic prerequisites)
    - Search query optimization for educational resources
    - Quality validation (no generic/vague responses)
    
    Args:
        transcript: Full lecture transcript text
        summary: Structured summary dict (title, summary, key_points, main_concepts)
        keywords: List of key terms from the lecture
    
    Returns:
        Tuple of (learning_gaps, search_queries) where:
        - learning_gaps: List of prerequisite concepts/skills (3-6 items)
        - search_queries: List of optimized search queries (5-8 items)
    
    Raises:
        ValueError: If API key not set or inputs invalid
        Exception: If analysis fails after all retries
    
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
                
                _logger.info("🤖 Analyzing gaps with Gemini 2.5 Flash...")
                
                # Configure Gemini
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # Build context from available information
                lecture_title = summary.get("title", "Unknown Lecture") if summary else "Unknown Lecture"
                lecture_summary = summary.get("summary", "") if summary else ""
                main_concepts = summary.get("main_concepts", keywords) if summary else keywords
                
                # Optimized prompt for pedagogical gap analysis
                prompt = f"""You are an expert educator analyzing a lecture for prerequisite knowledge.

LECTURE INFORMATION:
Title: {lecture_title}
Summary: {lecture_summary}
Key Concepts: {', '.join(main_concepts[:10])}

TRANSCRIPT EXCERPT:
{transcript[:2000]}...

Your task is to:
1. Identify 3-6 prerequisite concepts or skills students MUST know before this lecture
2. Generate 5-8 targeted search queries to find learning resources for these prerequisites

Focus on:
- Foundational knowledge (not just related topics)
- Specific skills or concepts (not generic "background knowledge")
- Prerequisites that would genuinely help understanding
- Search queries optimized for educational resources (tutorials, courses, explanations)

Generate a JSON response with this EXACT structure (no markdown, just raw JSON):
{{
  "learning_gaps": [
    "Specific prerequisite concept 1",
    "Specific prerequisite skill 2",
    "Foundational knowledge area 3"
  ],
  "search_queries": [
    "introduction to [concept] tutorial",
    "[skill] basics for beginners",
    "how to understand [topic] step by step"
  ]
}}

Return ONLY the JSON object, no other text."""

                # Generate analysis (blocking call, run in executor)
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
                    analysis_dict = json.loads(response_text)
                except json.JSONDecodeError as je:
                    _logger.warning(f"⚠️ JSON parse error: {je}. Response: {response_text[:200]}")
                    raise ValueError(f"Invalid JSON response from Gemini: {je}")
                
                # Validate structure
                required_keys = {"learning_gaps", "search_queries"}
                if not all(key in analysis_dict for key in required_keys):
                    missing = required_keys - set(analysis_dict.keys())
                    raise ValueError(f"Missing required keys in Gemini response: {missing}")
                
                # Extract and validate learning gaps
                learning_gaps = analysis_dict["learning_gaps"]
                if not isinstance(learning_gaps, list) or len(learning_gaps) < 2:
                    raise ValueError(
                        f"Invalid learning_gaps: expected list with 2+ items, got {type(learning_gaps)} "
                        f"with {len(learning_gaps) if isinstance(learning_gaps, list) else 0} items"
                    )
                
                # Filter out generic/vague gaps
                filtered_gaps = [
                    gap.strip() for gap in learning_gaps
                    if gap and len(gap.strip()) > 10  # At least 10 chars
                    and not gap.lower().startswith("basic understanding")  # Avoid generic
                    and not gap.lower().startswith("familiarity with")  # Avoid vague
                ][:6]  # Limit to 6 gaps
                
                if len(filtered_gaps) < 2:
                    raise ValueError(f"Too few quality learning gaps after filtering: {len(filtered_gaps)}")
                
                # Extract and validate search queries
                search_queries = analysis_dict.get("search_queries", [])
                if not isinstance(search_queries, list):
                    _logger.warning(f"⚠️ search_queries not a list: {type(search_queries)}")
                    search_queries = []
                
                # Filter out invalid queries
                filtered_queries = [
                    query.strip() for query in search_queries
                    if query and isinstance(query, str) and len(query.strip()) > 5  # At least 5 chars
                ][:8]  # Limit to 8 queries
                
                # If we got too few search queries, generate fallback from keywords + gaps
                if len(filtered_queries) < 3:
                    _logger.warning(
                        f"⚠️ Only {len(filtered_queries)} search queries from Gemini, "
                        f"generating fallback from gaps and keywords"
                    )
                    # Generate search queries from learning gaps + keywords
                    fallback_queries = []
                    for gap in filtered_gaps[:3]:
                        # Convert gap to search query (e.g., "Linear algebra" → "linear algebra tutorial for beginners")
                        fallback_queries.append(f"{gap} tutorial for beginners")
                        fallback_queries.append(f"learn {gap} step by step")
                    
                    for keyword in keywords[:3]:
                        fallback_queries.append(f"{keyword} explained simply")
                    
                    # Combine with any valid queries from Gemini
                    filtered_queries = filtered_queries + fallback_queries
                    filtered_queries = list(dict.fromkeys(filtered_queries))[:8]  # Deduplicate, limit to 8
                    
                    _logger.info(f"✅ Generated {len(filtered_queries)} search queries (with fallback)")
                
                _logger.info(
                    f"✅ Gap analysis generated: {len(filtered_gaps)} gaps, "
                    f"{len(filtered_queries)} search queries"
                )
                
                return filtered_gaps, filtered_queries
                
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
                    _logger.error(f"❌ Gap analysis failed after {max_retries} attempts: {e}")
                    raise
                    
            except ValueError as ve:
                # Validation errors - retry (might be transient API issue)
                if attempt < max_retries - 1 and ("JSON" in str(ve) or "Invalid" in str(ve)):
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
                    _logger.error(f"❌ Gemini gap analysis failed: {type(e).__name__}: {e}")
                    raise
        
        # Should never reach here
        raise Exception(f"Gap analysis failed after {max_retries} retry attempts")
        
    except Exception as e:
        _logger.error(f"❌ Fatal error in Gemini gap analysis: {e}")
        raise

    except Exception as e:
        _logger.error(f"Gemini gap analysis failed: {e}")
        raise
