import json
import random
import logging
from bs4 import BeautifulSoup
from mistralai.client import Mistral
from serpapi import GoogleSearch
from app.config import MISTRAL_API_KEY, SERP_API_KEY, SUMMARY_MODEL

logger = logging.getLogger(__name__)

def generate_search_queries(html_content: str) -> list:
    """Generate search queries from the content for SERP enrichment. Uses JSON mode."""
    try:
        soup = BeautifulSoup(str(html_content), 'html.parser')
        text = soup.get_text()[:3000]

        client = Mistral(api_key=MISTRAL_API_KEY)
        response = client.chat.complete(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": (
                    "Generate 7-10 different search queries based on this content. "
                    "Each query should be 5-12 words and search-friendly. "
                    "Return a JSON object with a single key 'queries' containing an array of strings. "
                    "Example: {\"queries\": [\"query one\", \"query two\"]}"
                )},
                {"role": "user", "content": text}
            ],
            temperature=0.55,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        import json
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        queries = [q.strip() for q in data.get('queries', []) if isinstance(q, str) and q.strip()]
        return queries or ["Recommended Content"]
    except Exception as e:
        logger.error(f"Query generation failed: {e}")
        return ["Recommended Content"]


def fetch_serp_content(query: str, search_type: str) -> dict | None:
    """Fetch news, video, or shopping results from SerpAPI."""
    engine_map = {
        'news': ('google_news', 'news_results'),
        'videos': ('google_videos', 'video_results'),
        'shopping': ('google_shopping', 'shopping_results'),
    }

    if search_type not in engine_map:
        return None

    engine, results_key = engine_map[search_type]

    try:
        params = {
            "api_key": SERP_API_KEY,
            "engine": engine,
            "q": query,
            "hl": "en",
            "gl": "us",
            "safe": "off",
        }
        if search_type != 'news':
            params["google_domain"] = "google.com"

        search = GoogleSearch(params)
        results = search.get_dict()

        if results_key in results:
            return {results_key: results[results_key]}
        return None
    except Exception as e:
        logger.error(f"SERP fetch failed ({search_type}): {e}")
        return None


def inject_serp_sections(soup, search_queries: list):
    """Inject news/video/shopping sections into the HTML."""
    content_types = ['videos', 'news', 'shopping']
    num_sections = random.choices([0, 1, 2], weights=[20, 40, 40])[0]

    if num_sections == 0:
        return

    selected = random.sample(content_types, k=num_sections)
    logger.info(f"Injecting SERP sections: {selected}")

    for content_type in selected:
        query = random.choice(search_queries)
        results = fetch_serp_content(query, content_type)

        if not results:
            continue

        section_html = _build_serp_section(soup, content_type, results, query)
        if section_html:
            main = soup.find('main') or soup.find('body')
            if main:
                footer = soup.find('footer')
                if footer:
                    footer.insert_before(section_html)
                else:
                    main.append(section_html)


def _build_serp_section(soup, content_type, results, query):
    """Build an HTML section for SERP content."""
    section = soup.new_tag('section', **{'class': 'serp-section my-8 p-6 rounded-lg shadow-lg'})

    title_tag = soup.new_tag('h2', **{'class': 'text-2xl font-bold mb-6'})
    title_text = _generate_section_title(content_type, query)
    title_tag.string = title_text
    section.append(title_tag)

    if content_type == 'news':
        items = results.get('news_results', [])[:3]
        for item in items:
            link_url = item.get('highlight', {}).get('link') or item.get('link')
            if not link_url:
                continue
            _append_news_card(soup, section, item, link_url)

    elif content_type == 'videos':
        items = [v for v in results.get('video_results', []) if v.get('link')][:2]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-2 gap-4'})
        for item in items:
            _append_video_card(soup, container, item)
        section.append(container)

    elif content_type == 'shopping':
        items = [p for p in results.get('shopping_results', []) if p.get('product_link')][:2]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-2 gap-6'})
        for item in items:
            _append_product_card(soup, container, item)
        section.append(container)

    return section


def _generate_section_title(content_type, query):
    words = query.split()[:3]
    topic = ' '.join(w.capitalize() for w in words) if words else "Related"

    patterns = {
        'news': [f"Latest on {topic}", f"{topic} Headlines", f"What's New in {topic}"],
        'videos': [f"Watch: {topic}", f"{topic} in Action", f"Explore {topic}"],
        'shopping': [f"Shop {topic}", f"Top {topic} Picks", f"{topic} Essentials"],
    }
    return random.choice(patterns.get(content_type, [f"Related {topic}"]))


def _append_news_card(soup, parent, item, link_url):
    a = soup.new_tag('a', href=link_url, target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline mb-4'})
    article = soup.new_tag('article', **{'class': 'p-4 rounded-lg transition-all hover:scale-[1.02] hover:shadow-md'})

    thumb = item.get('highlight', {}).get('thumbnail') or item.get('thumbnail')
    if thumb:
        img = soup.new_tag('img', src=thumb, **{'class': 'w-full h-48 object-cover rounded-lg mb-3'})
        article.append(img)

    h3 = soup.new_tag('h3', **{'class': 'text-lg font-semibold mb-2'})
    h3.string = item.get('highlight', {}).get('title') or item.get('title', 'Untitled')
    article.append(h3)

    if item.get('snippet'):
        p = soup.new_tag('p', **{'class': 'text-sm opacity-90'})
        p.string = item['snippet']
        article.append(p)

    a.append(article)
    parent.append(a)


def _append_video_card(soup, parent, item):
    a = soup.new_tag('a', href=item['link'], target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline'})
    div = soup.new_tag('div', **{'class': 'rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-all'})

    if item.get('thumbnail'):
        img = soup.new_tag('img', src=item['thumbnail'],
                          **{'class': 'w-full h-40 object-cover'})
        div.append(img)

    info = soup.new_tag('div', **{'class': 'p-3'})
    h4 = soup.new_tag('h4', **{'class': 'font-medium mb-1'})
    h4.string = item.get('title', 'Untitled Video')
    info.append(h4)

    if item.get('duration'):
        span = soup.new_tag('span', **{'class': 'text-xs opacity-70'})
        span.string = item['duration']
        info.append(span)

    div.append(info)
    a.append(div)
    parent.append(a)


def _append_product_card(soup, parent, item):
    a = soup.new_tag('a', href=item['product_link'], target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline'})
    div = soup.new_tag('div', **{'class': 'rounded-lg overflow-hidden shadow-md hover:shadow-lg transition-all'})

    if item.get('thumbnail'):
        img = soup.new_tag('img', src=item['thumbnail'],
                          **{'class': 'w-full aspect-square object-cover'})
        div.append(img)

    info = soup.new_tag('div', **{'class': 'p-4'})
    h4 = soup.new_tag('h4', **{'class': 'font-medium mb-2'})
    h4.string = item.get('title', 'Untitled')
    info.append(h4)

    if item.get('price'):
        price = soup.new_tag('p', **{'class': 'text-lg font-bold mb-1'})
        price.string = item['price']
        info.append(price)

    if item.get('source'):
        src = soup.new_tag('p', **{'class': 'text-sm opacity-70'})
        src.string = f"From {item['source']}"
        info.append(src)

    div.append(info)
    a.append(div)
    parent.append(a)
