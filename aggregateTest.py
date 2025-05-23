from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import ollama
import time
import json
from google import genai
from google.genai import types
from util.LLMClient.OllamaClient import OllamaClient
from util.LLMClient.GeminiClient import GeminiClient
client = genai.Client(api_key="AIzaSyB4fdbU163FTzyE2lXnI55jvlCLCFfdwzU")



class BiasDetail(BaseModel):
    bias_type: str = Field(description="The type of bias identified (e.g., Framing, Omission, Loaded Language).")
    explanation: str = Field(description="Explanation of why this is considered a bias in context.")
    evidence: str = Field(description="Specific quote or phrase from the article serving as evidence for the bias.")

class ArticleAnalysis(BaseModel):
    source_name: str = Field(description="The name of the news source for this article.")
    is_relevant: bool = Field(description="Whether the article was deemed relevant to the core news event.")
    relevance_reason: Optional[str] = Field(default=None, description="Reason if the article was deemed not relevant. Null if relevant.")
    identified_biases: List[BiasDetail] = Field(default_factory=list, description="List of biases identified in this article. Empty if no biases found or article irrelevant for bias analysis.")

class NewsOutput(BaseModel):
    news_title: str = Field(description="A  title of the summarized core news event identified from the relevant articles.")
    synthesized_neutral_report: str = Field(description="The synthesized, neutral news report based on relevant articles.")
    article_analyses: List[ArticleAnalysis] = Field(description="Analysis for each provided article source, including relevance and biases.")
    category: Literal["Politics", "Health", "Technology", "Sports", "Entertainment", "Business", "Other"] = Field(description="The most appropriate category of the news event from the predefined list.")


SYSTEM_INSTRUCTION = """
You are an expert, impartial journalist and media analyst. Your primary task is to analyze a collection of news articles and produce a structured JSON output adhering strictly to the provided schema.

Follow these steps meticulously:

1.  **Identify Core Event, Title, and Category:**
    a.  Carefully read ALL provided "INPUT ARTICLE #N" blocks.
    b.  Determine the single, central news event or topic that is common across the articles (or the primary focus if articles diverge significantly).
    c.  Formulate a neutral, concise 'news_title' reflecting this core event. This title should be objective and summarize the primary incident.
    d.  Determine the most appropriate 'category' for this core news event from the following predefined list: "Politics", "Health", "Technology", "Sports", "Entertainment", "Business", "Other". This category MUST be included in the 'category' field of the final JSON output.

2.  **Process Each Input Article Individually for Analysis:**
    You will process each "INPUT ARTICLE #N" (e.g., "INPUT ARTICLE #1", "INPUT ARTICLE #2", etc.) sequentially. For each article:
    a.  **Extract Source Name:** Identify the 'SOURCE_NAME_FOR_ARTICLE_#N' provided for the *current* input article. This exact name MUST be used in the 'source_name' field of this article's analysis object in the JSON output.
    b.  **Relevance Check:**
        i.  Assess if the *current* "INPUT ARTICLE #N" is primarily about the core event identified for the 'news_title'.
        ii. Set 'is_relevant' to true or false for this article.
        iii. If 'is_relevant' is false, provide a brief 'relevance_reason'. If true, 'relevance_reason' should be null.
    c.  **Bias Analysis (if relevant):**
        i.  If the *current* article is deemed 'is_relevant', analyze its "CONTENT_OF_ARTICLE_#N" for potential biases.
        ii. Common bias types include: Framing, Omission, Loaded Language, Spin, Sensationalism, Unsubstantiated Claims, False Balance, Partisan Bias, Attribution Bias. Use the most specific and appropriate type.
        iii. For each identified bias, create a `BiasDetail` object:
            -   'bias_type': The specific type of bias.
            -   'explanation': A clear explanation of *why* this specific content is considered a bias in the context of *this* article and the core event.
            -   'evidence': A direct, verbatim quote from "CONTENT_OF_ARTICLE_#N" that serves as evidence for this specific bias.
        iv. Populate the 'identified_biases' list for this article's analysis. If no biases are found, or if the article is not relevant, this list should be empty.
    d.  **Construct Article Analysis Object:** Create an `ArticleAnalysis` object for the *current* input article, ensuring all fields ('source_name', 'is_relevant', 'relevance_reason', 'identified_biases') are correctly populated according to the steps above.
    e.  Add this object to the 'article_analyses' list in the final JSON output.

3.  **Synthesize Neutral Report (from relevant articles ONLY):**
    a.  Identify all "INPUT ARTICLE #N" blocks that you marked as 'is_relevant' in Step 2.
    b.  Using ONLY the factual content from these relevant articles, write a 'synthesized_neutral_report'.
    c.  Focus strictly on verifiable facts, key events, figures, and attributed statements. Present information in a balanced and objective way.
    d.  If conflicting factual claims arise between *relevant* articles, acknowledge the discrepancy (e.g., "Source X reports [fact A], while Source Y reports [fact B]."). Do not attempt to resolve conflicts unless the articles themselves provide a resolution.
    e.  The tone must be strictly objective, impartial, and informative. Avoid speculation, personal opinions, or emotionally charged language not directly quoted from a source (and if quoted, attribute it).

**CRITICAL JSON Output Requirements:**
*   You MUST output your findings as a single, valid JSON object that conforms to the Pydantic schema provided (which will be derived from the `NewsOutput` model).
*   The 'article_analyses' list MUST contain exactly one analysis object for EACH "INPUT ARTICLE #N" that was provided in the input.
*   The order of objects in the 'article_analyses' list MUST correspond to the order of the "INPUT ARTICLE #N" blocks (e.g., the first object in the list analyzes "INPUT ARTICLE #1", the second analyzes "INPUT ARTICLE #2", and so on).
*   The 'source_name' field within each `ArticleAnalysis` object MUST be the exact string taken from the 'SOURCE_NAME_FOR_ARTICLE_#N' line associated with that input article block. DO NOT invent, shorten, or infer source names. Use the provided ones precisely.
*   The 'category' field in the main JSON output must be one of the predefined values: "Politics", "Health", "Technology", "Sports", "Entertainment", "Business", "Other".
"""

def format_articles_for_prompt(articles_with_sources: list[dict]) -> str:
    prompt_text = "--- START OF PROVIDED ARTICLES TO ANALYZE ---\n\n"
    for i, item in enumerate(articles_with_sources):
        prompt_text += f"--- INPUT ARTICLE #{i+1} ---\n" # Consistent numbering
        prompt_text += f"SOURCE_NAME_FOR_ARTICLE_#{i+1}: {item['source_name']}\n"
        prompt_text += f"CONTENT_OF_ARTICLE_#{i+1}:\n{item['content']}\n"
        prompt_text += f"--- END OF INPUT ARTICLE #{i+1} ---\n\n"
    prompt_text += "--- END OF PROVIDED ARTICLES TO ANALYZE ---"
    return prompt_text

start = time.time()

user_prompt_content = format_articles_for_prompt([
        {"source_name": "Al Jazeera", "content": open("demoNews/pahalgam_alzajeera.txt", "r", encoding="utf-8").read()},
        {"source_name": "OpIndia", "content": open("demoNews/pahalgam_opindia.txt", "r", encoding="utf-8").read()},
    ])

source_names_list = [
    "Al Jazeera",
    "OpIndia",
]
num_articles = len(source_names_list)
full_user_prompt = f"""
You are provided with {num_articles} input articles, clearly demarcated as "INPUT ARTICLE #1", "INPUT ARTICLE #2", etc.
The source names for these articles, in order, are: {', '.join(source_names_list)}.

Your task is to meticulously follow all instructions in the system prompt to analyze EACH of these {num_articles} input articles and generate the specified JSON output.
The 'article_analyses' list in your JSON output MUST contain exactly {num_articles} entries. The first entry must correspond to "INPUT ARTICLE #1" (source: {source_names_list[0]}), the second to "INPUT ARTICLE #2" (source: {source_names_list[1]}), and so on.

{user_prompt_content}

Remember to produce a single, valid JSON object strictly matching the schema provided in the system instructions (this schema is derived from the Pydantic models, including the 'category' field).
Pay EXTREME attention to correctly using the provided 'SOURCE_NAME_FOR_ARTICLE_#N' for each article's analysis in the output JSON.
Ensure the 'category' field is correctly populated from the allowed list.
"""

# response = ollama.generate(
#     options={
#         "temperature": 0.3,
#         "system": SYSTEM_INSTRUCTION,
#     },
#     prompt=full_user_prompt,  model='gemma3:12b',  format=NewsOutput.model_json_schema(),
# )

llmClient = OllamaClient(model_name="gemma3:12b")
response = llmClient.generateAggregateArticle(
    user_prompt=full_user_prompt,
    system_instruction=SYSTEM_INSTRUCTION,
    response_schema=NewsOutput,
)

# response = client.models.generate_content(
#     model="gemini-2.0-flash",
#     contents=full_user_prompt,
#     config={
#         "system_instruction": SYSTEM_INSTRUCTION,
#         "response_mime_type": "application/json",
#         "response_schema": NewsOutput,
#     },
# )
# Use the response as a JSON string.
print(response)

# print(response)

f = open("aggrResult.json", "w", encoding="utf-8")
f.write(response)
f.close()

end = time.time()

print("Time taken: ", end - start)