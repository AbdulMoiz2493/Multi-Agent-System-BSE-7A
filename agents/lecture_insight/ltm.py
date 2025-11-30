"""
Lecture Insight Agent - Long-Term Memory (LTM)
SQLite-based caching for lecture processing results.

Design Principles:
- Transactional integrity (ACID)
- Comprehensive error handling
- Configurable storage location
- Statistics tracking for optimization
"""

import hashlib
import json
import logging
import aiosqlite
import os
from typing import Optional, Dict, Any
from pathlib import Path

_logger = logging.getLogger(__name__)

# Configurable DB path (can be overridden via environment variable)
DB_PATH = os.getenv("LTM_DB_PATH", "ltm_lecture_insight.db")


async def init_db():
    """
    Initialize LTM database with schema and indices.
    
    Creates:
    - Main cache table with ACID-compliant structure
    - Index on audio_hash for fast lookups
    - Index on access_count for analytics
    
    Raises:
        Exception: If database initialization fails
    """
    try:
        # Ensure directory exists
        db_dir = Path(DB_PATH).parent
        if db_dir != Path('.'):
            db_dir.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Create main table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS lecture_cache (
                    cache_key TEXT PRIMARY KEY,
                    audio_hash TEXT NOT NULL,
                    preferences_json TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER NOT NULL DEFAULT 1,
                    CHECK (access_count >= 1)
                )
            """)
            
            # Create indices for performance
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audio_hash 
                ON lecture_cache(audio_hash)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_access_count 
                ON lecture_cache(access_count DESC)
            """)
            
            await db.commit()
        
        _logger.info(f"✅ Initialized LTM database at {DB_PATH}")
        
    except Exception as e:
        _logger.error(f"❌ Failed to initialize LTM database: {e}")
        raise


def _generate_cache_key(audio_data: str, preferences: dict) -> str:
    """
    Generate deterministic cache key from audio + preferences.
    
    Args:
        audio_data: Audio data (base64/url/stream identifier)
        preferences: Processing preferences dict
        
    Returns:
        SHA256 hash as cache key
    """
    # Create deterministic string from audio + preferences
    cache_input = f"{audio_data}|{json.dumps(preferences, sort_keys=True)}"
    return hashlib.sha256(cache_input.encode()).hexdigest()


async def lookup(audio_data: str, preferences: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if lecture processing result exists in cache.
    
    Uses atomic transaction to ensure statistics are always updated on cache hits.
    
    Args:
        audio_data: Audio data identifier (URL, base64, or stream ID)
        preferences: Processing preferences dict
        
    Returns:
        Cached output dict or None if not found
        
    Raises:
        Exception: If database operation fails (logged but not propagated)
    """
    cache_key = _generate_cache_key(audio_data, preferences)
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Use transaction for atomicity
            async with db.execute("BEGIN IMMEDIATE"):
                # Fetch result
                cursor = await db.execute(
                    "SELECT output_json FROM lecture_cache WHERE cache_key = ?",
                    (cache_key,)
                )
                row = await cursor.fetchone()
                
                if row:
                    # Update access statistics in same transaction
                    await db.execute(
                        """UPDATE lecture_cache 
                           SET last_accessed = CURRENT_TIMESTAMP, 
                               access_count = access_count + 1 
                           WHERE cache_key = ?""",
                        (cache_key,)
                    )
                    await db.commit()
                    
                    _logger.info(f"🎯 LTM cache HIT for key {cache_key[:12]}...")
                    
                    # Parse JSON with error handling
                    try:
                        return json.loads(row[0])
                    except json.JSONDecodeError as e:
                        _logger.error(f"⚠️ Corrupted cache entry for key {cache_key[:12]}: {e}")
                        # Delete corrupted entry
                        await db.execute("DELETE FROM lecture_cache WHERE cache_key = ?", (cache_key,))
                        await db.commit()
                        return None
        
        _logger.info(f"❌ LTM cache MISS for key {cache_key[:12]}...")
        return None
        
    except aiosqlite.OperationalError as e:
        _logger.error(f"⚠️ Database locked or unavailable during lookup: {e}")
        return None  # Graceful degradation: treat as cache miss
        
    except Exception as e:
        _logger.error(f"❌ Unexpected error during cache lookup: {e}")
        return None  # Graceful degradation


async def save(audio_data: str, preferences: Dict[str, Any], output: Dict[str, Any]):
    """
    Save lecture processing result to cache.
    
    Uses INSERT ... ON CONFLICT to preserve statistics when updating existing entries.
    If entry exists, only updates output_json and last_accessed, preserving created_at
    and access_count.
    
    Args:
        audio_data: Audio data identifier
        preferences: Processing preferences dict
        output: LectureInsightOutput dict to cache
        
    Raises:
        Exception: If database operation fails (logged but not propagated)
    """
    cache_key = _generate_cache_key(audio_data, preferences)
    audio_hash = hashlib.sha256(audio_data.encode()).hexdigest()
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Use INSERT with ON CONFLICT to preserve statistics
            await db.execute(
                """INSERT INTO lecture_cache 
                   (cache_key, audio_hash, preferences_json, output_json, created_at, last_accessed, access_count) 
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                   ON CONFLICT(cache_key) DO UPDATE SET
                       output_json = excluded.output_json,
                       last_accessed = CURRENT_TIMESTAMP
                   WHERE cache_key = excluded.cache_key""",
                (
                    cache_key,
                    audio_hash,
                    json.dumps(preferences, sort_keys=True),
                    json.dumps(output)
                )
            )
            await db.commit()
        
        _logger.info(f"💾 Saved to LTM cache: {cache_key[:12]}...")
        
    except aiosqlite.IntegrityError as e:
        _logger.error(f"⚠️ Data integrity issue while saving to cache: {e}")
        raise
        
    except aiosqlite.OperationalError as e:
        _logger.error(f"⚠️ Database locked or unavailable during save: {e}")
        raise
        
    except json.JSONEncodeError as e:
        _logger.error(f"❌ Failed to serialize output to JSON: {e}")
        raise ValueError(f"Invalid output format: {e}")
        
    except Exception as e:
        _logger.error(f"❌ Unexpected error during cache save: {e}")
        raise


async def get_stats() -> Dict[str, Any]:
    """
    Get LTM cache statistics.
    
    Returns:
        Dict with:
        - total_entries: Number of cached lectures
        - total_accesses: Cumulative access count across all entries
        - cache_size_mb: Approximate database file size
        - most_accessed: Top 5 most frequently accessed entries
        
    Raises:
        Exception: If database operation fails
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Total entries
            cursor = await db.execute("SELECT COUNT(*) FROM lecture_cache")
            total_entries = (await cursor.fetchone())[0]
            
            # Total accesses
            cursor = await db.execute("SELECT SUM(access_count) FROM lecture_cache")
            total_accesses = (await cursor.fetchone())[0] or 0
            
            # Calculate cache hit rate (accesses / entries)
            cache_hit_rate = (total_accesses / total_entries) if total_entries > 0 else 0
            
            # Most accessed entries
            cursor = await db.execute(
                """SELECT audio_hash, access_count, created_at, last_accessed
                   FROM lecture_cache 
                   ORDER BY access_count DESC 
                   LIMIT 5"""
            )
            most_accessed = await cursor.fetchall()
        
        # Get database file size
        try:
            db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
        except OSError:
            db_size_mb = 0
        
        return {
            "total_entries": total_entries,
            "total_accesses": total_accesses,
            "cache_hit_rate": round(cache_hit_rate, 2),
            "cache_size_mb": round(db_size_mb, 2),
            "most_accessed": [
                {
                    "audio_hash": row[0][:12] + "...",
                    "access_count": row[1],
                    "created_at": row[2],
                    "last_accessed": row[3]
                }
                for row in most_accessed
            ]
        }
        
    except Exception as e:
        _logger.error(f"❌ Failed to retrieve cache statistics: {e}")
        raise


async def cleanup_old_entries(days_old: int = 30) -> int:
    """
    Remove cache entries older than specified days that haven't been accessed recently.
    
    Args:
        days_old: Remove entries not accessed in this many days (default: 30)
        
    Returns:
        Number of entries removed
        
    Raises:
        Exception: If database operation fails
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """DELETE FROM lecture_cache 
                   WHERE datetime(last_accessed) < datetime('now', ? || ' days')""",
                (-days_old,)
            )
            await db.commit()
            deleted_count = cursor.rowcount
        
        if deleted_count > 0:
            _logger.info(f"🧹 Cleaned up {deleted_count} old cache entries (>{days_old} days)")
        
        return deleted_count
        
    except Exception as e:
        _logger.error(f"❌ Failed to cleanup old cache entries: {e}")
        raise


async def clear_cache() -> bool:
    """
    Clear all cache entries. Use with caution!
    
    Returns:
        True if successful
        
    Raises:
        Exception: If database operation fails
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM lecture_cache")
            await db.commit()
        
        _logger.warning("⚠️ LTM cache cleared completely")
        return True
        
    except Exception as e:
        _logger.error(f"❌ Failed to clear cache: {e}")
        raise
