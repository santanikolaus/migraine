import logging
import time
from collections.abc import Iterator
from typing import Any

import httpx

from clients.config import RedditConfig
from models.reddit import RedditComment, RedditPost

logger = logging.getLogger(__name__)

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"
RETRY_STATUSES = {401, 429, 500, 502, 503, 504}


class RedditClient:
    """Read-only, rate-limited access to one subreddit through Reddit's OAuth Data API."""

    def __init__(
        self,
        config: RedditConfig,
        client_id: str,
        client_secret: str,
        username: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = config
        self._auth = (client_id, client_secret)
        self._http = httpx.Client(
            headers={"User-Agent": config.user_agent.format(username=username)},
            timeout=config.timeout,
            transport=transport,
        )
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._last_request_at = 0.0

    def __enter__(self) -> "RedditClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def listing(self, sort: str) -> Iterator[RedditPost]:
        """Yield posts from a subreddit listing.

        Args:
            sort: Listing name such as new, hot or top; top covers all time

        Yields:
            Posts in listing order, up to pages_per_listing pages
        """
        params = {"t": "all"} if sort == "top" else {}
        yield from self._paginate(f"/r/{self._config.subreddit}/{sort}", params, self._config.pages_per_listing)

    def search(self, query: str) -> Iterator[RedditPost]:
        """Yield posts matching a keyword search restricted to the subreddit.

        Args:
            query: Reddit search query

        Yields:
            Posts ordered by relevance, up to search_pages pages
        """
        params = {"q": query, "restrict_sr": "1", "sort": "relevance", "t": "all"}
        yield from self._paginate(f"/r/{self._config.subreddit}/search", params, self._config.search_pages)

    def comments(self, post_id: str) -> list[RedditComment]:
        """Fetch the comment tree of a post, flattened in depth-first order.

        Collapsed "load more" stubs are skipped, so very large threads come back partially.

        Args:
            post_id: Post id without the t3_ prefix

        Returns:
            All loaded comments; authors are not kept
        """
        payload = self._get(f"/r/{self._config.subreddit}/comments/{post_id}", {"limit": 500})
        return list(self._flatten(payload[1]["data"]["children"]))

    def _paginate(self, path: str, params: dict[str, str], max_pages: int) -> Iterator[RedditPost]:
        after = None
        for _ in range(max_pages):
            page_params = {**params, "limit": self._config.page_size}
            if after:
                page_params["after"] = after
            page = self._get(path, page_params)["data"]
            for child in page["children"]:
                if child["kind"] == "t3":
                    yield RedditPost.model_validate(child["data"])
            after = page.get("after")
            if not after:
                return

    def _flatten(self, children: list[dict[str, Any]]) -> Iterator[RedditComment]:
        for child in children:
            if child["kind"] != "t1":
                continue
            yield RedditComment.model_validate(child["data"])
            replies = child["data"].get("replies")
            if replies:
                yield from self._flatten(replies["data"]["children"])

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        for attempt in range(self._config.max_retries + 1):
            self._throttle()
            response = self._http.get(
                API_BASE + path,
                params={**params, "raw_json": 1},
                headers={"Authorization": f"bearer {self._access_token()}"},
            )
            if response.status_code not in RETRY_STATUSES or attempt == self._config.max_retries:
                response.raise_for_status()
                return response.json()
            if response.status_code == 401:
                self._token = None
                continue
            wait = float(response.headers.get("X-Ratelimit-Reset", 2**attempt))
            logger.warning("HTTP %d on %s, retrying in %.0fs", response.status_code, path, wait)
            time.sleep(wait)

    def _access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        response = self._http.post(TOKEN_URL, auth=self._auth, data={"grant_type": "client_credentials"})
        response.raise_for_status()
        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.monotonic() + payload["expires_in"] - 60
        return self._token

    def _throttle(self) -> None:
        wait = self._last_request_at + self._config.request_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()
