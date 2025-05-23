from pymongo.server_api import ServerApi
from pymongo.mongo_client import MongoClient

import os
from dotenv import load_dotenv
load_dotenv()

_client = None

def getClient():
    global _client
    if _client is not None:
        try:
            _client.admin.command('ping')
            print("Client Already Present, Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)
            _client = None
        return _client
   # Provide the mongodb atlas url to connect python to mongodb using pymongo
    CONNECTION_STRING = os.getenv('MONGO_URL')  
    _client = MongoClient(CONNECTION_STRING, server_api=ServerApi('1'))
    try:
        _client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
        _client = None
    return _client
  
# This is added so that many files can reuse the function get_database()
if __name__ == "__main__":   
   # Get the database
    dbname = getClient()