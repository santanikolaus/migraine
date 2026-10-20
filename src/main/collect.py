import argparse
import logging

import yaml

from clients.reddit_client import RedditClient
from models.constants import DATA_DIR, SEARCH_TERMS
from models.settings import AppSettings
from services.collect import Collector

logger = logging.getLogger(__name__)


def main() -> None:
    """Collect r/migraine posts and comments into data/reddit/."""
    parser = argparse.ArgumentParser(description="Collect subreddit posts and comments for private case research.")
    parser.add_argument("--query", action="append", help="search query; repeatable, replaces search_terms.yaml")
    parser.add_argument("--no-listings", action="store_true", help="only run searches, skip new/top/hot listings")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = AppSettings()
    queries = args.query or yaml.safe_load(SEARCH_TERMS.read_text())["queries"]
    listings = [] if args.no_listings else settings.reddit.listings

    with RedditClient(
        settings.reddit, settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET, settings.REDDIT_USERNAME
    ) as client:
        out_path = Collector(client, DATA_DIR / "reddit").run(listings, queries)
    logger.info("wrote %s", out_path)


if __name__ == "__main__":
    main()
