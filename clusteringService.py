from util.mongoConn import getClient
import time
from util.chroma.ChromaClient import getCollection, setEmbeddingFunction
from DTOs.AggregateArticle import AggregateArticle
from DTOs.NewsOutputSchema import NewsOutput
from util.LLMClient.GeminiClient import GeminiClient
from bson import ObjectId
import datetime
from chromadb.utils import embedding_functions
from util.LLMClient.GeminiClient import GeminiClient
from util.LLMClient.AIConfig import FULL_USER_PROMPT, SYSTEM_INSTRUCTION

PARSED_ARTICLES_COLLECTION = "parsedArticles"
AGGREGATED_ARTICLES_COLLECTION = "aggregatedArticles"
DISTANCE_THRESHOLD = 0.8219 # Adjust as needed

def getArticlesToAggregate(db, collection_name, limit=10):
    collection = db[collection_name]
    query = {"is_aggregated": False}
    oldest_records = collection.find(query).sort("creationDate", 1).limit(limit)
    return list(oldest_records)




def createClusterAndStore(article):
    aggregate_article = AggregateArticle(
        title="",
        content="",
        last_updated=datetime.datetime.now().isoformat(),
        constituent_article_ids=[article['_id']],
        article_analysis=[],
        is_aggregated=False,
        needs_aggregation=True
    )
    insert_result = aggregated_articles_collection.insert_one(aggregate_article.model_dump(by_alias=True))
    new_aggregate_mongo_id = insert_result.inserted_id
    print(f"Created new cluster {new_aggregate_mongo_id} for article: {article['_id']}")
    parsed_articles_collection.update_one(
        {"_id": article["_id"]},
        {"$set": {"is_aggregated": True, "aggregation_status": "success"}}
    )
    print(f"Marked article {article['_id']} as aggregated successfully.")
    return new_aggregate_mongo_id

def updateClusterAndStore(article, aggregateId):
    aggregate_article = aggregated_articles_collection.find_one({"_id": ObjectId(aggregateId)})
    if aggregate_article:
        # Update the existing cluster with the new article
        update_document = {
            "$addToSet": {"constituent_article_ids": article['_id']},
            "$set": {"last_updated": datetime.datetime.now().isoformat(), "needs_aggregation": True}
        }
        aggregated_articles_collection.update_one(
            {"_id": ObjectId(aggregateId)},
            update_document
        )
        print(f"Updated cluster {aggregateId} with article: {article['_id']}")
        parsed_articles_collection.update_one(
            {"_id": article["_id"]},
            {"$set": {"is_aggregated": True, "aggregation_status": "success"}}
        )
        print(f"Marked article {article['_id']} as aggregated successfully.")
    else:
        # Create a new cluster if it doesn't exist
        aggregateId = createClusterAndStore(article)

def storeInChroma(article, aggregateId):
    articleCollection.add(
        ids=[str(article["_id"])],
        documents=[article["content"]],
        metadatas=[{'aggregate_article_id': str(aggregateId), 'original_article_id': str(article["_id"]), 'source': article['source'], 'title': article['title']}],
    )
    print(f"Stored article {article['_id']} in ChromaDB with aggregate ID {aggregateId}")

if __name__ == "__main__":
    mongoClient = getClient()
    db = mongoClient["reportDB"]
    parsed_articles_collection = db[PARSED_ARTICLES_COLLECTION]
    aggregated_articles_collection = db[AGGREGATED_ARTICLES_COLLECTION]
    model_name = "all-MiniLM-L6-v2"
    emb_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name, device="cpu", normalize_embeddings=True)
    setEmbeddingFunction(emb_func)
    articleCollection = getCollection("article_vectors")

    llmClient = GeminiClient()

    while True:
        articles_to_process = getArticlesToAggregate(db, PARSED_ARTICLES_COLLECTION, limit=1000)
        
        if not articles_to_process:
            print("No new articles to aggregate.")
            time.sleep(10)
            continue

        print(f"Found {len(articles_to_process)} articles to process for aggregation.")

        for article in articles_to_process:
            article_id = article["_id"]
            # Assuming 'text' contains the main article content and 'url' its source URL
            article_text = article['content']
            article_source = article['source']

            if not article_text:
                print(f"Article {article_id} has no text content. Skipping and marking as aggregated.")
                parsed_articles_collection.update_one(
                    {"_id": article_id},
                    {"$set": {"is_aggregated": True, "aggregation_status": "skipped_no_text"}}
                )
                continue
            query_results = articleCollection.query(
                query_texts=[article_text],
                n_results=1,
                include=['metadatas', 'distances']
            )
            if (len(query_results['ids'][0]) == 0 or 
                len(query_results['distances'][0]) == 0 or 
                len(query_results['metadatas'][0]) == 0):
                print("ChromaDB is empty.")
                aggregateId = createClusterAndStore(article)
                storeInChroma(article, aggregateId)
                continue
            else:
                if(query_results['ids'][0][0] == str(article_id)):
                    print(f"Article {article_id} is already in ChromaDB. Skipping.")
                    parsed_articles_collection.update_one(
                        {"_id": article_id},
                        {"$set": {"is_aggregated": True, "aggregation_status": "skipped_already_in_chromadb"}}
                    )
                    continue
                if(query_results['distances'][0][0] < DISTANCE_THRESHOLD):
                    print(article['title']+" was found to be similar to an existing article in ChromaDB.")
                    aggregateId = query_results['metadatas'][0][0]['aggregate_article_id']
                    updateClusterAndStore(article, aggregateId)
                    storeInChroma(article, aggregateId)
                else:
                    print(article['title']+" was not found to be similar to an existing article in ChromaDB.")
                    aggregateId = createClusterAndStore(article)
                    storeInChroma(article, aggregateId)
        print("Finished processing batch. Waiting for next poll...")

