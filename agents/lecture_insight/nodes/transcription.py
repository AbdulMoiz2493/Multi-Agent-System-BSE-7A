"""
Transcription Node - Converts audio to text using AssemblyAI

Production-ready implementation with:
- Retry logic with exponential backoff
- Support for URLs, local files, and base64 audio
- Dynamic language detection from preferences
- Async-friendly execution
- Comprehensive error handling
"""

import logging
import os
import asyncio
import base64
import tempfile
from typing import Dict, Any, Tuple
from pathlib import Path

_logger = logging.getLogger(__name__)


async def transcribe_audio(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transcribe audio input to text using AssemblyAI.
    
    Supports:
    - HTTP/HTTPS URLs (remote audio files)
    - Local file paths (uploaded files)
    - Base64-encoded audio (inline audio data)
    
    Args:
        state: Current workflow state with:
            - audio_input: dict with type, data, format
            - preferences: dict with optional language setting
        
    Returns:
        Updated state with:
            - transcript: Transcribed text
            - audio_duration: Duration in seconds
            - error: Error message if transcription failed
    
    Example:
        >>> state = {
        ...     "audio_input": {
        ...         "type": "url",
        ...         "data": "https://example.com/lecture.mp3",
        ...         "format": "mp3"
        ...     },
        ...     "preferences": {"language": "en"}
        ... }
        >>> result = await transcribe_audio(state)
        >>> print(result["transcript"])
    """
    _logger.info("🎤 Starting audio transcription...")
    
    try:
        audio_input = state.get("audio_input", {})
        audio_data = audio_input.get("data")
        audio_format = audio_input.get("format", "mp3")
        audio_type = audio_input.get("type", "url")
        
        if not audio_data:
            raise ValueError("No audio data provided in audio_input.data")
        
        # Get language preference (default to English)
        preferences = state.get("preferences", {})
        language = preferences.get("language", "en")
        
        # Transcribe using AssemblyAI
        transcript, duration = await _transcribe_with_assemblyai(
            audio_data=audio_data,
            audio_format=audio_format,
            audio_type=audio_type,
            language=language
        )
        
        state["transcript"] = transcript
        state["audio_duration"] = duration
        
        word_count = len(transcript.split())
        _logger.info(f"✅ Transcription complete: {word_count} words, {duration}s audio")
        return state
        
    except Exception as e:
        _logger.error(f"❌ Transcription failed: {type(e).__name__}: {e}")
        state["error"] = f"Transcription error: {str(e)}"
        state["transcript"] = ""
        state["audio_duration"] = 0
        return state


async def _transcribe_with_assemblyai(
    audio_data: str,
    audio_format: str,
    audio_type: str,
    language: str = "en"
) -> Tuple[str, float]:
    """
    Transcribe audio using AssemblyAI API with retry logic and base64 support.
    
    Supports:
    - Local file paths (e.g., "sample_audios/lecture.mp3")
    - HTTP URLs (e.g., "https://example.com/audio.mp3")
    - Base64-encoded audio (decoded to temporary file)
    
    Process:
    1. Decode base64 (if needed) or prepare file/URL
    2. Upload local file to AssemblyAI (SDK handles this)
    3. Create transcription job with optimal config
    4. Poll until complete (SDK handles polling)
    5. Return transcript + duration
    
    Features:
    - Retry on network errors (3 attempts with exponential backoff)
    - Temporary file cleanup for base64 audio
    - File size validation (max 500 MB)
    - Detailed error logging and progress tracking
    
    Args:
        audio_data: Audio source (URL, file path, or base64 string)
        audio_format: Audio format (mp3, wav, m4a, etc.)
        audio_type: Type of audio input (url, file, base64, stream)
        language: Language code (default: "en")
    
    Returns:
        Tuple of (transcript_text, duration_in_seconds)
    
    Raises:
        ValueError: If API key not set or invalid input
        Exception: If transcription fails after all retries
    
    Requires:
        ASSEMBLYAI_API_KEY or ASSEMBLY_AI_API_KEY environment variable
    """
    max_retries = 3
    retry_delay = 2  # seconds
    temp_file_path = None
    
    try:
        # Get API key (check both common variations)
        api_key = os.getenv("ASSEMBLYAI_API_KEY") or os.getenv("ASSEMBLY_AI_API_KEY")
        if not api_key:
            raise ValueError(
                "AssemblyAI API key not found. Set ASSEMBLYAI_API_KEY or ASSEMBLY_AI_API_KEY "
                "environment variable."
            )
        
        for attempt in range(max_retries):
            try:
                import assemblyai as aai
                
                if attempt > 0:
                    _logger.info(f"🔄 Retry attempt {attempt + 1}/{max_retries}")
                
                _logger.info(f"🎙️ Transcribing {audio_type} audio with AssemblyAI (language: {language})")
                
                # Configure AssemblyAI client
                aai.settings.api_key = api_key
                
                # Transcription configuration optimized for educational content
                config = aai.TranscriptionConfig(
                    speech_model=aai.SpeechModel.best,  # Best accuracy
                    language_code=language,  # Dynamic language from preferences
                    punctuate=True,  # Add punctuation
                    format_text=True,  # Format text properly
                    speaker_labels=False  # Single speaker assumed
                )
                
                transcriber = aai.Transcriber(config=config)
                
                # Prepare audio input based on type
                audio_source = None
                
                if audio_type == "url" or audio_data.startswith("http://") or audio_data.startswith("https://"):
                    # Remote URL
                    _logger.info(f"📡 Transcribing from URL: {audio_data[:60]}...")
                    audio_source = audio_data
                    
                elif audio_type == "file" or os.path.isfile(audio_data):
                    # Local file
                    file_size_mb = os.path.getsize(audio_data) / (1024 * 1024)
                    _logger.info(f"📁 Uploading local file: {audio_data} ({file_size_mb:.2f} MB)")
                    
                    if file_size_mb > 500:
                        raise ValueError(f"File too large: {file_size_mb:.2f} MB (AssemblyAI max: 500 MB)")
                    
                    audio_source = audio_data
                    
                elif audio_type == "base64" or audio_data.startswith("data:audio"):
                    # Base64-encoded audio - decode to temporary file
                    _logger.info("🔄 Decoding base64 audio to temporary file...")
                    
                    # Extract base64 data (remove data URL prefix if present)
                    if audio_data.startswith("data:"):
                        # Format: data:audio/mp3;base64,<base64_data>
                        base64_data = audio_data.split(",", 1)[1]
                    else:
                        base64_data = audio_data
                    
                    # Decode base64
                    audio_bytes = base64.b64decode(base64_data)
                    
                    # Create temporary file
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=f".{audio_format}",
                        prefix="lecture_audio_"
                    )
                    temp_file.write(audio_bytes)
                    temp_file.close()
                    temp_file_path = temp_file.name
                    
                    file_size_mb = len(audio_bytes) / (1024 * 1024)
                    _logger.info(f"📁 Created temp file: {temp_file_path} ({file_size_mb:.2f} MB)")
                    
                    if file_size_mb > 500:
                        raise ValueError(f"Decoded audio too large: {file_size_mb:.2f} MB (max: 500 MB)")
                    
                    audio_source = temp_file_path
                    
                else:
                    raise ValueError(
                        f"Invalid audio input. Expected URL, file path, or base64 data. "
                        f"Got type='{audio_type}', data preview: {audio_data[:50]}..."
                    )
                
                # Submit transcription (blocking call, run in executor for async compatibility)
                _logger.info("⏳ Submitting transcription job to AssemblyAI...")
                start_time = asyncio.get_event_loop().time()
                
                loop = asyncio.get_event_loop()
                transcript_obj = await loop.run_in_executor(
                    None,
                    transcriber.transcribe,
                    audio_source
                )
                
                elapsed_time = asyncio.get_event_loop().time() - start_time
                _logger.info(f"⏱️ Transcription completed in {elapsed_time:.1f}s")
                
                # Check status
                if transcript_obj.status == aai.TranscriptStatus.error:
                    error_msg = transcript_obj.error or "Unknown AssemblyAI error"
                    raise Exception(f"AssemblyAI error: {error_msg}")
                
                # Extract results
                transcript_text = transcript_obj.text
                if not transcript_text or not transcript_text.strip():
                    raise Exception("AssemblyAI returned empty transcript")
                
                # Duration in milliseconds → seconds
                duration_seconds = (
                    transcript_obj.audio_duration / 1000.0
                    if transcript_obj.audio_duration
                    else 0
                )
                
                word_count = len(transcript_text.split())
                _logger.info(
                    f"✅ Transcription successful: {word_count} words, "
                    f"{duration_seconds:.1f}s audio, {len(transcript_text)} characters"
                )
                
                return transcript_text.strip(), round(duration_seconds, 2)
                
            except ImportError:
                _logger.error("❌ AssemblyAI SDK not installed")
                raise ValueError(
                    "AssemblyAI SDK not installed. Install with: pip install assemblyai"
                )
                
            except (ConnectionError, TimeoutError, OSError) as e:
                # Network-related errors - retry with exponential backoff
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    _logger.warning(f"⚠️ Network error: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    _logger.error(f"❌ Transcription failed after {max_retries} attempts: {e}")
                    raise
                    
            except Exception as e:
                # Other errors - don't retry
                _logger.error(f"❌ Transcription error: {type(e).__name__}: {e}")
                raise
        
        # Should never reach here
        raise Exception(f"Transcription failed after {max_retries} retry attempts")
    
    finally:
        # Cleanup temporary file if created
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                _logger.info(f"🗑️ Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                _logger.warning(f"⚠️ Failed to cleanup temp file {temp_file_path}: {e}")
