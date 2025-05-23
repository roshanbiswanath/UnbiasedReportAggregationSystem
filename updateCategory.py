import os
import json
from pymongo.errors import ConnectionFailure, OperationFailure
from util.mongoConn import getClient

# --- MongoDB Configuration ---
# !!! IMPORTANT: Replace these placeholders with your actual MongoDB connection details if not using mongoConn.py's environment variables !!!
# MONGO_URI = "mongodb://localhost:27017/" # Removed
DATABASE_NAME = "reportDB"    # Example: "news_aggregator" - Kept, as getClient() likely returns client, not db
COLLECTION_NAME = "aggregatedArticles"  # Example: "articles" - Kept, as getClient() likely returns client, not collection
# --- End MongoDB Configuration ---

OUTPUT_DIR = "c:\\\\Users\\\\rosha\\\\OneDrive\\\\Documents\\\\The Unbiased Report\\\\AI Aggregation System\\\\output"

def update_mongodb_records():
    """
    Iterates through JSON files in the OUTPUT_DIR, reads news_title and category,
    and updates the corresponding document in MongoDB using getClient() from mongoConn.
    """
    client = getClient() # Use getClient()

    if not client:
        print("Failed to get MongoDB client from mongoConn. Exiting.")
        return
    
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    
    updated_count = 0
    not_found_count = 0
    error_count = 0
    processed_files = 0

    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(OUTPUT_DIR, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                news_title = data.get("news_title")
                category = data.get("category")

                if not news_title:
                    print(f"Skipping {filename}: 'news_title' not found.")
                    error_count += 1
                    continue
                
                if category is None: # Allow for empty string categories, but not missing ones
                    print(f"Skipping {filename}: 'category' not found or is null.")
                    # If you want to treat missing category as an error, increment error_count
                    # error_count += 1 
                    continue

                # Find the document by title and update its category
                # Using a field that is more likely to be unique, like an ID, is generally better if available.
                # For this script, we'll use news_title as per the requirement.
                result = collection.update_one(
                    {"title": news_title},  # Filter to find the document
                    {"$set": {"category": category}}  # Update operation
                )

                if result.matched_count > 0:
                    if result.modified_count > 0:
                        print(f"Updated category for '{news_title}' in MongoDB.")
                        updated_count += 1
                    else:
                        print(f"Category for '{news_title}' was already up-to-date.")
                        # You might count this differently if needed
                else:
                    print(f"No document found in MongoDB with title '{news_title}' (from file {filename}).")
                    not_found_count += 1
                
                processed_files +=1

            except json.JSONDecodeError:
                print(f"Error decoding JSON from {filename}.")
                error_count += 1
            except OperationFailure as e:
                print(f"MongoDB operation failed for {filename}: {e}")
                error_count += 1
            except Exception as e:
                print(f"An unexpected error occurred with file {filename}: {e}")
                error_count += 1
                
    client.close()
    print("\n--- Update Summary ---")
    print(f"Total JSON files processed: {processed_files}")
    print(f"Successfully updated documents: {updated_count}")
    print(f"Documents not found in MongoDB (by title): {not_found_count}")
    print(f"Files with errors (JSON decode, missing fields, DB operation): {error_count}")

if __name__ == "__main__":
    # Removed MONGO_URI check as it's no longer directly used here.
    # The warning for DATABASE_NAME and COLLECTION_NAME remains relevant if they are placeholders.
    if DATABASE_NAME == "your_database_name" or COLLECTION_NAME == "your_collection_name":
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! WARNING: Default MongoDB DATABASE_NAME or COLLECTION_NAME is being used. !!!")
        print("!!! Please open updateCategory.py and update them if they are not correctly  !!!")
        print("!!! configured for the client obtained from mongoConn.py.                    !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    
    print(f"Starting MongoDB update process for files in: {OUTPUT_DIR}")
    update_mongodb_records()
    print("Process finished.")
