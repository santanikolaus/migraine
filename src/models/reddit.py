from pydantic import BaseModel


class RedditComment(BaseModel):
    id: str
    parent_id: str
    body: str
    score: int
    created_utc: float
    depth: int


class RedditPost(BaseModel):
    id: str
    title: str
    selftext: str = ""
    score: int
    num_comments: int
    created_utc: float
    link_flair_text: str | None = None
    permalink: str
    sources: list[str] = []
    comments: list[RedditComment] = []
