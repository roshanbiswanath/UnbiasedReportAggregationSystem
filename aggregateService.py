\
# filepath: c:\\Users\\rosha\\OneDrive\\Documents\\The Unbiased Report\\AI Aggregation System\\aggregateService.py
import time
import datetime
from bson import ObjectId

from util.mongoConn import getClient
from util.LLMClient.GeminiClient import GeminiClient
from util.LLMClient.AIConfig import FULL_USER_PROMPT, SYSTEM_INSTRUCTION # Ensure these are correctly defined
from DTOs.NewsOutputSchema import NewsOutput
from DTOs.AggregateArticle import AggregateArticle
# Ensure AggregateArticle DTO is available if needed for direct instantiation, though not directly used here for updates
# from DTOs.AggregateArticle import AggregateArticle 

import dotenv
# Load environment variables from .env file
dotenv.load_dotenv()

PARSED_ARTICLES_COLLECTION = "parsedArticles"
AGGREGATED_ARTICLES_COLLECTION = "aggregatedArticles"

def format_articles_for_prompt(articles) -> str:
    prompt_text = "--- START OF PROVIDED ARTICLES TO ANALYZE ---\n\n"
    for i in range(1, len(articles) + 1):
        item = articles[i - 1]
        prompt_text += f"--- INPUT ARTICLE #{i} ---\n" # Consistent numbering
        prompt_text += f"SOURCE_NAME_FOR_ARTICLE_#{i}: {item['source']}\n"
        prompt_text += f"CONTENT_OF_ARTICLE_#{i}:\n{item['content']}\n"
        prompt_text += f"--- END OF INPUT ARTICLE #{i} ---\n\n"
    prompt_text += "--- END OF PROVIDED ARTICLES TO ANALYZE ---"
    return prompt_text

def generateUserPrompt(articlePromptContent, sourceNameList):
    num_articles = len(sourceNameList)
    return FULL_USER_PROMPT.format(
        num_articles,
        ", ".join(sourceNameList),
        num_articles,
        num_articles,
        sourceNameList[0],
        sourceNameList[1] if num_articles > 1 else "",
        articlePromptContent
    )

def getArticlesToAggregate(db, collection_name, limit=10):
    collection = db[collection_name]
    # Updated query to fetch if is_aggregated is False OR needs_aggregation is True
    query = {
        "$or": [
            {"is_aggregated": False},
            {"needs_aggregation": True}
        ]
    }
    oldest_records = collection.find(query).sort("creationDate", 1).limit(limit)
    return list(oldest_records)

def createAggregateArticleAndStore(articles, clusterArticle):
    response = llmClient.generateAggregateArticle(
        user_prompt=generateUserPrompt(
            format_articles_for_prompt(articles),
            [article['source'] for article in articles]
        ),
        system_instruction=SYSTEM_INSTRUCTION,
        response_schema=NewsOutput,
    )
    newsOutput = None
    try:
        newsOutput = NewsOutput.model_validate_json(response)
        fileName = newsOutput.news_title
        fileName = fileName.replace(" ", "_").replace("/", "_")
        f = open("./output/{}.json".format(fileName), "w", encoding="utf-8")
        f.write(response)
        f.close()
        print(f"Successfully saved output to file: {fileName}.json")
        existingArticle = AggregateArticle(
            _id=clusterArticle["_id"],
            title=newsOutput.news_title,
            content=newsOutput.synthesized_neutral_report,
            last_updated=datetime.datetime.now().isoformat(),
            constituent_article_ids=clusterArticle["constituent_article_ids"],
            article_analysis=newsOutput.article_analyses,
            is_aggregated=True,
            needs_aggregation=False,
            categpory=newsOutput.category
        )
        # Update the existing cluster with the new article
        aggregated_articles_collection.update_one(
            {"_id": ObjectId(clusterArticle["_id"])},
            {"$set": existingArticle.model_dump(by_alias=True)}
        )

        # aggregated_articles_collection.update_one(
        #     {"_id": clusterArticle["_id"]},
        #     {"$set": {
        #         "is_aggregated": True,
        #         "needs_aggregation": False,
        #         "last_updated": datetime.datetime.now().isoformat(),
        #         "article_analysis": newsOutput.article_analyses,
        #         "title": newsOutput.news_title,
        #         "content": newsOutput.synthesized_neutral_report,
        #         }}
        # )
        print(f"Updated cluster {clusterArticle['_id']} with aggregation results.")
    except Exception as e:
        print(f"Error validating news output: {e}")
    # print(newsOutput)
    return newsOutput


if __name__ == "__main__":
    mongo_client = getClient()
    db = mongo_client["reportDB"]
    aggregated_articles_collection = db[AGGREGATED_ARTICLES_COLLECTION]

    llmClient = GeminiClient() 

    print("Aggregate Service started. Polling for articles needing LLM processing...")

    while True:
        clusteredArticles = getArticlesToAggregate(db, AGGREGATED_ARTICLES_COLLECTION, limit=10)
        # print(clusteredArticles)
        if not clusteredArticles:
            print("No articles found for aggregation. Waiting for new articles...")
            time.sleep(10)
            continue
        print(f"Found {len(clusteredArticles)} articles to process for aggregation.")
        # Prepare the articles for the LLM
        for clusterArticle in clusteredArticles:
            constituentArticles = []
            for constituentArticleId in clusterArticle["constituent_article_ids"]:
                constituentArticle = db[PARSED_ARTICLES_COLLECTION].find_one({"_id": ObjectId(constituentArticleId)})
                if constituentArticle:
                    constituentArticles.append(constituentArticle)
            createAggregateArticleAndStore(constituentArticles, clusterArticle)
