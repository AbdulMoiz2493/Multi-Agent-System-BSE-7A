import logging
import json
from typing import Optional, List
import chromadb
from chromadb.config import Settings
import hashlib

_logger = logging.getLogger(__name__)

# Initialize ChromaDB client (persistent vector database)
client = None
collection = None

async def init_db():
    global client, collection
    try:
        client = chromadb.PersistentClient(
            path="./ltm_assignment_coach",
            settings=Settings(anonymized_telemetry=False)
        )
        collection = client.get_or_create_collection(
            name="assignment_coach_memory",
            metadata={"description": "Long-term memory for assignment coaching"}
        )
        _logger.info(f"Initialized Assignment Coach LTM with ChromaDB at ./ltm_assignment_coach")
    except Exception as e:
        _logger.error(f"Failed to initialize ChromaDB: {e}")
        raise

async def lookup(input_request: str) -> Optional[str]:
    """Search for similar requests in vector database"""
    try:
        if not collection:
            return None
        
        # Parse input to create search query
        if isinstance(input_request, str):
            try:
                request_data = json.loads(input_request)
            except:
                request_data = {"request": input_request}
        else:
            request_data = input_request
            
        # Create search text from key fields
        payload = request_data.get("payload", {})
        search_text = f"{payload.get('assignment_title', '')} {payload.get('subject', '')} {payload.get('assignment_description', '')}"
        
        if not search_text.strip():
            return None
        
        # Query vector DB for similar assignments
        results = collection.query(
            query_texts=[search_text],
            n_results=1
        )
        
        if results and results['documents'] and len(results['documents'][0]) > 0:
            # Check similarity threshold (distances are returned)
            if results['distances'][0][0] < 0.3:  # Similarity threshold
                _logger.info(f"LTM cache hit for similar assignment")
                return results['metadatas'][0][0].get('output')
        
        return None
    except Exception as e:
        _logger.error(f"Error during LTM lookup: {e}")
        return None

async def save(input_request: str, output_response: str):
    """Save request-response pair to vector database"""
    try:
        if not collection:
            return
        
        # Parse input
        if isinstance(input_request, str):
            try:
                request_data = json.loads(input_request)
            except:
                request_data = {"request": input_request}
        else:
            request_data = input_request
        
        payload = request_data.get("payload", {})
        
        # Create document text for embedding
        doc_text = f"{payload.get('assignment_title', '')} {payload.get('subject', '')} {payload.get('assignment_description', '')}"
        
        # Generate unique ID
        doc_id = hashlib.sha256(input_request.encode() if isinstance(input_request, str) else json.dumps(input_request).encode()).hexdigest()
        
        # Store in vector DB
        collection.add(
            documents=[doc_text],
            metadatas=[{
                "input": json.dumps(request_data) if not isinstance(input_request, str) else input_request,
                "output": output_response,
                "timestamp": str(datetime.now())
            }],
            ids=[doc_id]
        )
        
        _logger.info(f"Saved to Assignment Coach LTM with ID {doc_id}")
    except Exception as e:
        _logger.error(f"Error saving to LTM: {e}")

from datetime import datetime
