import chromadb
from chromadb.utils import embedding_functions

# Initialize local ChromaDB client
client = chromadb.PersistentClient(path="./chroma_db")

# Use default embedding function for MVP (SentenceTransformers)
emb_fn = embedding_functions.DefaultEmbeddingFunction()

# Create or get collection for jobs
jobs_collection = client.get_or_create_collection(
    name="jobs",
    embedding_function=emb_fn
)

def add_jobs_to_vector_db(jobs: list[dict]):
    """
    Adds a list of jobs to ChromaDB.
    Expected job dict format:
    {
        "id": "job_uuid",
        "description": "Job description text here...",
        "metadata": {
            "title": "AI Engineer",
            "company": "Tech Corp",
            "location": "Remote"
        }
    }
    """
    ids = [job["id"] for job in jobs]
    documents = [job["description"] for job in jobs]
    metadatas = [job.get("metadata", {}) for job in jobs]

    jobs_collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

def search_jobs(query_text: str, n_results: int = 5):
    """
    Searches for jobs matching the query text.
    Returns the top n_results.
    """
    results = jobs_collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    return results
