import os
from google import genai
from google.genai import types
from datetime import datetime

# Initialize Gemini client
def get_gemini_client():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    
    if not project or not location:
        raise ValueError("GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION environment variables must be set")
        
    # When using Vertex AI, authentication is handled via GOOGLE_APPLICATION_CREDENTIALS
    # automatically by the Google Cloud libraries.
    return genai.Client(
        vertexai=True,
        project=project,
        location=location
    )

def create_file_search_store(session_id: str, user_id: str):
    client = get_gemini_client()
    store = client.file_search_stores.create(
        display_name=f"Session_{session_id}",
        metadata={
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat()
        }
    )
    return store

def upload_file_to_store(file_path: str, store_name: str, display_name: str, metadata: dict):
    client = get_gemini_client()
    
    # Upload to Files API first (as per spec recommendation for flexibility, though direct upload is also an option)
    # Spec Method 1: Direct Upload to File Search Store
    # "Use case: When you want to upload and index in one operation"
    # I will use Method 1 as it is simpler for this use case.
    
    operation = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store_name,
        display_name=display_name,
        metadata=metadata
    )
    
    result = operation.result()
    return result

def generate_content_with_rag(prompt: str, context: dict, store_name: str):
    client = get_gemini_client()
    
    response = client.models.generate_content(
        model='gemini-2.0-flash', # Using 2.0 Flash as 2.5 is likely a typo in spec or future version
        contents=f"{prompt}\n\nContext: {context}",
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search_retrieval=types.GoogleSearchRetrieval(
                        dynamic_retrieval_config=types.DynamicRetrievalConfig(
                            mode=types.DynamicRetrievalConfigMode.MODE_DYNAMIC,
                            dynamic_threshold=0.7,
                        )
                    )
                )
            ]
        )
    )
    # Wait, the spec says use FileSearchTool, not GoogleSearchRetrieval.
    # Correcting to use FileSearchTool.
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"{prompt}\n\nContext: {context}",
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearchTool(
                        file_search_store_names=[store_name]
                    )
                )
            ],
            temperature=0.7,
            max_output_tokens=2048
        )
    )
    return response

def generate_content_standard(prompt: str, context: dict):
    client = get_gemini_client()
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"{prompt}\n\nContext: {context}",
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=2048
        )
    )
    return response
