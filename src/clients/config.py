from pydantic import BaseModel


class RedditConfig(BaseModel):
    subreddit: str
    user_agent: str
    request_interval: float
    timeout: float
    max_retries: int
    page_size: int
    listings: list[str]
    pages_per_listing: int
    search_pages: int
