from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from DTOs.NewsOutputSchema import ArticleAnalysis
class AggregateArticle(BaseModel):
    _id: Optional[ObjectId]
    title: str = Field(..., description="The title of the article")
    content: str = Field(..., description="The content of the article")
    last_updated: Optional[str] = Field(default=None, description="The last updated date of the article")
    constituent_article_ids: List[ObjectId] = Field(default_factory=list, description="List of MongoDB ObjectIds of the constituent news articles")
    article_analysis: List[ArticleAnalysis] = Field(default_factory=list, description="List of article analyses for the constituent articles")
    is_aggregated: bool = Field(default=True, description="Flag to indicate if the article is an aggregate article")
    needs_aggregation: bool = Field(default=False, description="Flag to indicate if the article needs aggregation")
    class Config:
        arbitrary_types_allowed = True  # To allow ObjectId
        json_encoders = {ObjectId: str}  # To serialize ObjectId to str for JSON
        schema_extra = {
            "example": {
                "title": "Sample Aggregate Article Title",
                "content": "This is a sample content for an aggregated article.",
                "last_updated": "2023-10-01T12:00:00Z",
                "constituent_article_ids": [
                    "60d5ec49f72f3c58e4f6a2b1",
                    "60d5ec49f72f3c58e4f6a2b2"
                ]
            }
        }

    def __str__(self):
        return f"AggregateArticle(title={self.title}, content={self.content}, last_updated={self.last_updated}, constituent_article_ids={self.constituent_article_ids})"










