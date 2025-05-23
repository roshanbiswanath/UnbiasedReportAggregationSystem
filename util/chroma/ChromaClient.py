import chromadb

_client = None
_embedding_function = None

def setEmbeddingFunction(embedding_function):
    global _embedding_function
    _embedding_function = embedding_function

def getClient():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path="./chroma_db")
    return _client

def getCollection(name):
    client = getClient()
    collection = client.get_or_create_collection(name, embedding_function=_embedding_function)
    if collection is None:
        raise Exception("Failed to create or get collection")
    return collection