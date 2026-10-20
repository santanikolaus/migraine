import json

import httpx
import pytest

from clients.config import RedditConfig
from clients.reddit_client import RedditClient
from services.collect import Collector

CONFIG = RedditConfig(
    subreddit="migraine",
    user_agent="script:test:v0 (by /u/{username})",
    request_interval=0,
    timeout=5,
    max_retries=2,
    page_size=2,
    listings=["new"],
    pages_per_listing=5,
    search_pages=1,
)


def post(post_id: str, num_comments: int = 0) -> dict:
    return {
        "kind": "t3",
        "data": {
            "id": post_id,
            "title": f"title {post_id}",
            "selftext": "text",
            "author": "someone",
            "score": 1,
            "num_comments": num_comments,
            "created_utc": 1.0,
            "permalink": f"/r/migraine/comments/{post_id}/",
        },
    }


def comment(comment_id: str, depth: int, replies: list | None = None) -> dict:
    return {
        "kind": "t1",
        "data": {
            "id": comment_id,
            "parent_id": "t3_a",
            "body": f"body {comment_id}",
            "author": "someone",
            "score": 1,
            "created_utc": 1.0,
            "depth": depth,
            "replies": {"data": {"children": replies}} if replies else "",
        },
    }


def listing(children: list, after: str | None) -> dict:
    return {"data": {"children": children, "after": after}}


class FakeReddit:
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.rate_limited_once = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if path == "/api/v1/access_token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if path == "/r/migraine/new":
            if request.url.params.get("after") == "t3_b":
                return httpx.Response(200, json=listing([post("c")], None))
            return httpx.Response(200, json=listing([post("a", 2), post("b")], "t3_b"))
        if path == "/r/migraine/search":
            if not self.rate_limited_once:
                self.rate_limited_once = True
                return httpx.Response(429, headers={"X-Ratelimit-Reset": "0"})
            return httpx.Response(200, json=listing([post("a", 2), post("d")], None))
        if path == "/r/migraine/comments/a":
            tree = [comment("x", 0, [comment("y", 1)]), {"kind": "more", "data": {}}]
            return httpx.Response(200, json=[listing([post("a")], None), listing(tree, None)])
        return httpx.Response(404)


@pytest.fixture
def fake() -> FakeReddit:
    return FakeReddit()


@pytest.fixture
def client(fake: FakeReddit) -> RedditClient:
    return RedditClient(CONFIG, "id", "secret", "me", transport=httpx.MockTransport(fake))


def test_listing_follows_after_cursor(client: RedditClient) -> None:
    assert [p.id for p in client.listing("new")] == ["a", "b", "c"]


def test_requests_carry_token_and_user_agent(client: RedditClient, fake: FakeReddit) -> None:
    list(client.listing("new"))
    api_calls = [c for c in fake.calls if c.url.host == "oauth.reddit.com"]
    assert all(c.headers["Authorization"] == "bearer tok" for c in api_calls)
    assert all(c.headers["User-Agent"] == "script:test:v0 (by /u/me)" for c in fake.calls)
    assert sum(c.url.path == "/api/v1/access_token" for c in fake.calls) == 1


def test_search_retries_after_rate_limit(client: RedditClient) -> None:
    assert [p.id for p in client.search("aura")] == ["a", "d"]


def test_comments_flatten_nested_replies_and_skip_more(client: RedditClient) -> None:
    comments = client.comments("a")
    assert [(c.id, c.depth) for c in comments] == [("x", 0), ("y", 1)]


def test_collector_dedupes_and_drops_authors(client: RedditClient, tmp_path) -> None:
    out_path = Collector(client, tmp_path).run(["new"], ["aura"])
    rows = [json.loads(line) for line in out_path.read_text().splitlines()]

    assert [r["id"] for r in rows] == ["a", "b", "c", "d"]
    assert rows[0]["sources"] == ["listing:new", "search:aura"]
    assert [c["id"] for c in rows[0]["comments"]] == ["x", "y"]
    assert "someone" not in out_path.read_text()
