import logging
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from clients.reddit_client import RedditClient
from models.reddit import RedditPost

logger = logging.getLogger(__name__)


class Collector:
    """Gathers posts from listings and searches, attaches their comments and writes JSONL."""

    def __init__(self, client: RedditClient, out_dir: Path) -> None:
        self._client = client
        self._out_dir = out_dir

    def run(self, listings: list[str], queries: list[str]) -> Path:
        """Collect deduplicated posts with comments into a timestamped JSONL file.

        Each post is written as soon as its comments are fetched, so an interrupted run keeps its progress.

        Args:
            listings: Listing names to page through, e.g. new, top, hot
            queries: Search queries restricted to the subreddit

        Returns:
            Path of the written JSONL file
        """
        posts: dict[str, RedditPost] = {}
        for sort in listings:
            self._merge(posts, self._client.listing(sort), f"listing:{sort}")
        for query in queries:
            self._merge(posts, self._client.search(query), f"search:{query}")
        logger.info("collected %d unique posts, fetching comments", len(posts))

        self._out_dir.mkdir(parents=True, exist_ok=True)
        out_path = self._out_dir / f"reddit_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for i, post in enumerate(posts.values(), 1):
                if post.num_comments:
                    post.comments = self._client.comments(post.id)
                f.write(post.model_dump_json() + "\n")
                logger.info("%d/%d %s comments=%d", i, len(posts), post.id, len(post.comments))
        return out_path

    def _merge(self, posts: dict[str, RedditPost], found: Iterable[RedditPost], source: str) -> None:
        count = 0
        for post in found:
            posts.setdefault(post.id, post).sources.append(source)
            count += 1
        logger.info("%s: %d posts", source, count)
