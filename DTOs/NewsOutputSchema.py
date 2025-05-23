from pydantic import BaseModel, Field
from typing import List, Optional, Literal

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
    category: Literal["Politics", "Health", "Technology", "Sports", "Entertainment", "Business"] = Field(description="The category of the news event.")