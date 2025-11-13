import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def create_openai_chat_client(model, config, model_version=None, api_version=None, **kwargs):
    """
    Creates a chat client using Google's Gemini API via LangChain.
    
    Args:
        model: Model name (e.g., "gemini-1.5-pro", "gemini-1.5-flash")
        config: Configuration dict (currently unused but kept for compatibility)
        model_version: Optional model version suffix (ignored for Google API)
        api_version: Optional API version (ignored for Google API)
        **kwargs: Additional keyword arguments passed to ChatGoogleGenerativeAI
    
    Returns:
        ChatGoogleGenerativeAI client instance
    """
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it before running.")
    
    # Create Google Generative AI chat client
    llm_chat = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=google_api_key,
        temperature=0.7,
        **kwargs
    )
    
    return llm_chat
