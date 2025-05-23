import ollama

class OllamaClient():
    """
    Client implementation using the Ollama library.
    """

    def __init__(self, model_name: str = "gemma3:4b"):
        self.model_name = model_name

    def generateAggregateArticle(self, user_prompt: str, system_instruction: str, response_schema) -> str:
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=user_prompt,
                system=system_instruction,
                format=response_schema.model_json_schema(),
            )
            print(response)
            return response.response
        except Exception as e:
            print(f"Error during Ollama API call: {e}")
            return "Error: Could not parse article using Ollama."
