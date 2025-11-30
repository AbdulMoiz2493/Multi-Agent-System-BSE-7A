"""
Aggregation Node - Ranks and deduplicates resources
"""

import logging
from typing import Dict, Any, List
from collections import defaultdict

_logger = logging.getLogger(__name__)


async def aggregate_results(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregate, rank, and deduplicate articles and videos.
    
    Args:
        state: Current workflow state with 'articles' and 'videos'
        
    Returns:
        Updated state with ranked and deduplicated resources
    """
    _logger.info("📊 Aggregating and ranking resources...")
    
    try:
        articles = state.get("articles", [])
        videos = state.get("videos", [])
        preferences = state.get("preferences", {})
        
        # Deduplicate by URL
        articles = _deduplicate_by_url(articles)
        videos = _deduplicate_by_url(videos)
        
        # Sort by relevance score
        articles = sorted(articles, key=lambda x: x.get("relevance_score", 0), reverse=True)
        videos = sorted(videos, key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Apply resource limit
        limit = preferences.get("resource_limit", 10)
        article_limit = limit // 2
        video_limit = limit - article_limit
        
        articles = articles[:article_limit]
        videos = videos[:video_limit]
        
        # Update state
        state["articles"] = articles
        state["videos"] = videos
        
        _logger.info(f"✅ Aggregation complete: {len(articles)} articles, {len(videos)} videos after ranking")
        return state
        
    except Exception as e:
        _logger.error(f"❌ Aggregation failed: {e}")
        state["error"] = f"Aggregation error: {str(e)}"
        return state


def _deduplicate_by_url(resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate resources based on URL.
    Keep the one with highest relevance score.
    """
    seen = {}
    
    for resource in resources:
        url = resource.get("url", "")
        score = resource.get("relevance_score", 0)
        
        if url not in seen or score > seen[url].get("relevance_score", 0):
            seen[url] = resource
    
    return list(seen.values())


def _calculate_diversity_score(resources: List[Dict[str, Any]]) -> float:
    """
    Calculate diversity score based on source variety.
    Higher score = more diverse sources (better learning experience).
    """
    if not resources:
        return 0.0
    
    sources = defaultdict(int)
    for resource in resources:
        source = resource.get("source", "unknown")
        sources[source] += 1
    
    # Shannon diversity index
    total = len(resources)
    diversity = 0.0
    for count in sources.values():
        if count > 0:
            p = count / total
            diversity -= p * (p ** 0.5)  # Simplified diversity metric
    
    return round(diversity, 2)
