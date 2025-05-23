# filepath: c:\\Users\\rosha\\OneDrive\\Documents\\The Unbiased Report\\AI Aggregation System\\testChroma.py
from util.chroma.ChromaClient import getCollection, setEmbeddingFunction
from chromadb.utils import embedding_functions
import argparse

# --- ChromaDB Setup ---
# These should match the settings in your clusteringService.py
CHROMA_COLLECTION_NAME = "article_vectors"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2" # or your chosen model

def initialize_chroma():
    """Initializes and returns the ChromaDB collection."""
    try:
        emb_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_NAME, 
            device="cpu", # or "cuda" if you have a GPU and want to use it
            normalize_embeddings=True
        )
        # If your ChromaClient.py has a global way to set this, call it.
        # Otherwise, you might pass emb_func to getCollection if it expects it.
        setEmbeddingFunction(emb_func) 
        collection = getCollection(CHROMA_COLLECTION_NAME)
        print(f"Successfully connected to ChromaDB collection: {CHROMA_COLLECTION_NAME}")
        return collection
    except Exception as e:
        print(f"Error initializing ChromaDB: {e}")
        return None

def get_titles_for_cluster(collection, cluster_id_to_find: str):
    """
    Retrieves and prints titles of articles for a given cluster_id.
    The cluster_id corresponds to 'aggregate_article_id' in metadata.
    """
    if not collection:
        print("ChromaDB collection not initialized.")
        return

    print(f"\\nSearching for articles in cluster (aggregate_article_id): {cluster_id_to_find}")
    
    try:
        # Query ChromaDB using a metadata filter
        results = collection.get(
            where={"aggregate_article_id": cluster_id_to_find},
            include=["metadatas"] # We only need metadatas to get the title
        )
        
        metadatas = results.get('metadatas')
        
        if not metadatas:
            print(f"No articles found for cluster ID: {cluster_id_to_find}")
            return

        print(f"Found {len(metadatas)} article(s) in cluster {cluster_id_to_find}:")
        for i, meta in enumerate(metadatas):
            title = meta.get('title', 'N/A') # Safely get title, default to 'N/A'
            original_article_id = meta.get('original_article_id', 'N/A')
            print(f"  {i+1}. Title: {title} (Original Article ID: {original_article_id})")
            
    except Exception as e:
        print(f"An error occurred while querying ChromaDB: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get article titles for a given cluster ID from ChromaDB.")
    parser.add_argument("cluster_id", type=str, help="The cluster ID (aggregate_article_id) to search for.")
    
    args = parser.parse_args()
    
    target_cluster_id = args.cluster_id
    
    if not target_cluster_id:
        print("Cluster ID cannot be empty. Please provide a cluster_id.")
    else:
        article_collection = initialize_chroma()
        if article_collection:
            get_titles_for_cluster(article_collection, target_cluster_id)
