import os
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# 1. Environment and Path Setup
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# 2. Global Settings (Must match ingestion.py for vector compatibility)
Settings.llm = GoogleGenAI(
    model="gemini-3-flash-preview", 
    api_key=os.getenv("GEMINI_API_KEY")
)
Settings.embed_model = GoogleGenAIEmbedding(
    model_name="models/gemini-embedding-001", 
    api_key=os.getenv("GEMINI_API_KEY")
)

def query_aether(prompt: str):
    project_name = os.getenv("PROJECT_NAME", "default")
    folder = project_name.lower().replace(" ", "_")
    storage_dir = Path("./storage") / folder
    
    if not storage_dir.exists():
        raise FileNotFoundError(f"Storage directory {storage_dir} not found. Run ingestion.py first.")

    # 3. Load the index from the local JSON files
    storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
    index = load_index_from_storage(storage_context)

    # 4. Create the Query Engine
    # streaming=True allows for faster perceived response times
    query_engine = index.as_query_engine(streaming=False)
    
    response = query_engine.query(prompt)
    return response

if __name__ == "__main__":
    # Test Query: Replace this with any question about Vanguard
    test_query = "What is the relationship between base_scout.py and scout_core.py?"
    
    print(f"Querying Aether: {test_query}\n")
    result = query_aether(test_query)
    print(f"RESULT:\n{result}")