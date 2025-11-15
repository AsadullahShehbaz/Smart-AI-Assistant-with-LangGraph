"""
Memory storage and retrieval
"""
import time
import hashlib
import sqlite3
import atexit
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, PayloadSchemaType
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver
import config
# Suppress warnings
import warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='torch')


# ============ Qdrant Setup ============
qdrant_client = QdrantClient(
    url=config.QDRANT_URL,
    api_key=config.QDRANT_API_KEY
)

embedding_model = HuggingFaceEmbeddings(
    model_name=config.EMBEDDING_MODEL
)


# Create collection if needed
def setup_qdrant():
    """Setup Qdrant collection (run once)"""
    try:
        collections = qdrant_client.get_collections().collections
        exists = any(col.name == config.COLLECTION_NAME for col in collections)
        
        if not exists:
            qdrant_client.create_collection(
                collection_name=config.COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print(f"✅ Created collection: {config.COLLECTION_NAME}")
        
        # Create index
        try:
            qdrant_client.create_payload_index(
                collection_name=config.COLLECTION_NAME,
                field_name="thread_id",
                field_schema=PayloadSchemaType.KEYWORD
            )
        except:
            pass  # Index already exists
        
        try:
            qdrant_client.create_payload_index(
                collection_name=config.COLLECTION_NAME,
                field_name="role",
                field_schema=PayloadSchemaType.KEYWORD
            )
        except:
            pass
    except Exception as e:
        print(f"⚠️ Qdrant setup error: {e}")

setup_qdrant()


# ============ Memory Functions ============
def generate_point_id(thread_id, message_text, timestamp):
    """Create unique ID for memory"""
    unique_string = f"{thread_id}_{message_text[:50]}_{timestamp}"
    return int(hashlib.md5(unique_string.encode()).hexdigest()[:16], 16) % (10**10)


def store_memory(thread_id, message_text, role):
    """
    Save message to memory
    
    Args:
        thread_id: conversation ID
        message_text: the message
        role: "user" or "assistant"
    """
    try:
        # Convert text to vector
        embedding = embedding_model.embed_query(message_text)
        timestamp = time.time()
        point_id = generate_point_id(str(thread_id), message_text, timestamp)
        
        # Create point
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "thread_id": str(thread_id),
                "text": message_text,
                "role": role,
                "timestamp": timestamp
            }
        )
        
        # Save to Qdrant
        qdrant_client.upsert(
            collection_name=config.COLLECTION_NAME,
            points=[point]
        )
        
    except Exception as e:
        print(f"⚠️ Error storing memory: {e}")


def retrieve_memory(thread_id, query, limit=5):
    """
    Get relevant past messages
    
    Args:
        thread_id: conversation ID
        query: current message
        limit: how many memories to get
    
    Returns:
        List of past messages
    """
    try:
        # Convert query to vector
        query_vector = embedding_model.embed_query(query)
        
        # Search Qdrant
        results = qdrant_client.search(
            collection_name=config.COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
            query_filter={
                "must": [{"key": "thread_id", "match": {"value": str(thread_id)}}]
            }
        )
        
        # Return text only
        return [r.payload.get("text", "") for r in results if r.payload.get("text")]
        
    except Exception as e:
        print(f"⚠️ Error retrieving memory: {e}")
        return []


# ============ SQLite Checkpointer ============
# Create database connection
conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# Close connection when program exits
def cleanup():
    conn.close()
    print("🔒 Database closed")

atexit.register(cleanup)


def get_all_threads():
    """Get list of all conversation IDs"""
    threads = set()
    try:
        for checkpoint in checkpointer.list(None):
            t = checkpoint.config.get("configurable", {}).get("thread_id")
            if t:
                threads.add(t)
    except Exception as e:
        print(f"⚠️ Error getting threads: {e}")
    
    return list(threads)


def generate_conversation_title(thread_id, first_message):
    """Generate smart title from first message using LLM"""
    try:
        from agent import llm
        
        # Create a focused prompt for title generation
        prompt = f"""Generate a concise 3-5 word title for a conversation that starts with:
"{first_message[:150]}"

Requirements:
- Must be 3-5 words maximum
- Capture the main topic
- No quotes or punctuation
- Title case format

Title:"""
        
        response = llm.invoke(prompt)
        title = response.content.strip().strip('"').strip("'")
        
        # Ensure it's not too long
        words = title.split()
        if len(words) > 5:
            title = ' '.join(words[:5])
        
        # Store in Qdrant with special marker
        store_memory(thread_id, f"TITLE:{title}", "system")
        return title
        
    except Exception as e:
        print(f"⚠️ Error generating title: {e}")
        # Fallback to first 30 chars
        return first_message[:30] + "..." if len(first_message) > 30 else first_message


def get_conversation_title(thread_id):
    """Get conversation title, generating one if needed."""
    thread_id_str = str(thread_id)
    
    try:
        # 1. Check for existing smart-generated title
        results, _ = qdrant_client.scroll(
            collection_name=config.COLLECTION_NAME,
            scroll_filter={
                "must": [
                    {"key": "thread_id", "match": {"value": thread_id_str}},
                    {"key": "role", "match": {"value": "system"}}
                ]
            },
            limit=10,
            with_payload=["text"]
        )
        
        for point in results:
            if point.payload.get("text", "").startswith("TITLE:"):
                return point.payload.get("text")[6:]  # Return text after "TITLE:"

        # 2. No title exists, get all user messages and find the first one
        results, _ = qdrant_client.scroll(
            collection_name=config.COLLECTION_NAME,
            scroll_filter={
                "must": [
                    {"key": "thread_id", "match": {"value": thread_id_str}},
                    {"key": "role", "match": {"value": "user"}}
                ]
            },
            limit=100,
            with_payload=["text", "timestamp"]
        )
        
        if results:
            # Sort by timestamp to get the earliest message
            sorted_results = sorted(results, key=lambda x: x.payload.get("timestamp", 0))
            first_user_message = sorted_results[0].payload.get("text", "")
            
            if first_user_message:
                # Generate and store the title
                title = generate_conversation_title(thread_id, first_user_message)
                return title

        # 3. Final Fallback: Short UUID
        return f"Chat {thread_id_str[:8]}"
        
    except Exception as e:
        print(f"⚠️ Error in get_conversation_title: {e}")
        return f"Chat {thread_id_str[:8]}"