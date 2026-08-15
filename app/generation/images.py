import random
import logging
import gevent
from serpapi import GoogleSearch
from app.config import SERP_API_KEY

logger = logging.getLogger(__name__)

def fetch_image_for_tag(img_tag):
    """Fetch a real image URL for an <img> tag based on its alt text."""
    alt = img_tag.get('alt', '').strip()
    if not alt:
        return

    try:
        params = {
            "api_key": SERP_API_KEY,
            "engine": "google_images",
            "q": alt,
            "google_domain": "google.com",
            "hl": "en",
            "gl": "us",
            "safe": "off",
            "num": "5"
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        images = results.get('images_results', [])
        if images:
            chosen = random.choice(images[:min(5, len(images))])
            img_tag['src'] = chosen.get('original', chosen.get('thumbnail', ''))
            logger.info(f"Fetched image for: {alt}")
        else:
            logger.warning(f"No images found for: {alt}")
    except Exception as e:
        logger.error(f"Image fetch failed for '{alt}': {e}")


def fetch_all_images(soup):
    """Fetch images in parallel using gevent."""
    img_tags = soup.find_all('img')
    workers = [gevent.spawn(fetch_image_for_tag, img) for img in img_tags]
    gevent.joinall(workers)
    return len(img_tags)
