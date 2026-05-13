from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class NewsSentimentQueryParams(BaseModel):
    query_type: str = "news_sentiment_query"
    tickers: List[str] = Field(..., min_length=1)
    requested_field: Optional[str] = Field("news")
    compare_with: Optional[List[str]] = Field(None, description="Tickers to compare sentiment with")
    days: Optional[int] = Field(None, ge=1)
    weeks: Optional[int] = Field(None, ge=1)
    months: Optional[int] = Field(None, ge=1)

    @field_validator('requested_field')
    def validate_field(cls, v):
        allowed = {'news', 'sentiment', 'social_volume', 'positive_news', 'negative_news',
                   'news_sentiment_score', 'social_sentiment_score', 'news_volume'}
        if v is not None and v not in allowed:
            raise ValueError(f"requested_field must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}