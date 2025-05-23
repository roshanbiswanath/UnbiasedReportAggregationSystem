from google import genai
import os
import dotenv
# Load environment variables from .env file
dotenv.load_dotenv()

class GeminiClient():
    """
    Client implementation using the Gemini API.
    """
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.clients = []
        self.clientId = 0
        keyList = os.environ["GEMINI_API_KEYS"].split(",")
        print(os.environ["GEMINI_API_KEYS"])
        for key in keyList:
            try:
                self.clients.append(genai.Client(api_key=key))
            except Exception as e:
                print(f"Failed to configure Gemini API with key ending ...{key[-4:]}: {e}")
        print(self.clients)
    def generateAggregateArticle(self, user_prompt: str, system_instruction: str, response_schema) -> str:
        try:
            response = self.clients[self.clientId].models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config={
                    "system_instruction": system_instruction,
                    "response_schema": response_schema,
                    "response_mime_type": "application/json",
                }
            )
            self.clientId = (self.clientId + 1) % len(self.clients)
            return response.text
        except Exception as e:
            # Handle potential errors during API call
            print(f"Error during Gemini API call: {e}")
            return None
