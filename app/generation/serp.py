import json
import random
import logging
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from app.ai import complete
from app.config import SERP_API_KEY

logger = logging.getLogger(__name__)

def generate_search_queries(html_content: str) -> list:
    """Generate search queries from the content for SERP enrichment. Uses JSON mode."""
    try:
        soup = BeautifulSoup(str(html_content), 'html.parser')
        text = soup.get_text()[:3000]

        raw = complete(
            'summary',
            [
                {"role": "system", "content": (
                    "Generate 7-10 different search queries based on this content. "
                    "Each query should be 5-12 words and search-friendly. "
                    "Return a JSON object with a single key 'queries' containing an array of strings. "
                    "Example: {\"queries\": [\"query one\", \"query two\"]}"
                )},
                {"role": "user", "content": text}
            ],
            temperature=0.55,
            max_tokens=2000,
            json_mode=True
        )

        data = json.loads(raw)
        queries = [q.strip() for q in data.get('queries', []) if isinstance(q, str) and q.strip()]
        return queries or ["Recommended Content"]
    except Exception as e:
        logger.error(f"Query generation failed: {e}")
        return ["Recommended Content"]


# SerpAPI engines we can query, mapped to their result key.
ENGINE_MAP = {
    'news': ('google_news', 'news_results'),
    'videos': ('google_videos', 'video_results'),
    'shopping': ('google_shopping', 'shopping_results'),
    'jobs': ('google_jobs', 'jobs_results'),
    'recipes': ('google_recipes', 'recipes_results'),
    'books': ('google_books', 'books_results'),
    'movies': ('google_movies', 'showtimes'),
    'events': ('google_events', 'events_results'),
    'local': ('google_local', 'local_results'),
    'related_questions': ('google_related_questions', 'related_questions'),
    'scholar': ('google_scholar', 'organic_results'),
}


def fetch_serp_content(query: str, search_type: str) -> dict | None:
    """Fetch enrichment results from any supported SerpAPI engine."""
    if not SERP_API_KEY:
        return None

    if search_type not in ENGINE_MAP:
        return None

    engine, results_key = ENGINE_MAP[search_type]

    try:
        params = {
            "api_key": SERP_API_KEY,
            "engine": engine,
            "q": query,
            "hl": "en",
            "gl": "us",
            "safe": "off",
        }
        if search_type not in ('news', 'movies', 'events', 'local'):
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
    """Inject news/video/shopping sections into the HTML, scattered through the
    page content rather than all stacked at the bottom."""
    content_types = list(ENGINE_MAP.keys())
    num_sections = random.choices([0, 1, 2, 3], weights=[15, 35, 35, 15])[0]

    if num_sections == 0:
        return

    selected = random.sample(content_types, k=num_sections)
    logger.info(f"Injecting SERP sections: {selected}")

    sections = []
    for content_type in selected:
        query = random.choice(search_queries)
        results = fetch_serp_content(query, content_type)
        if not results:
            continue
        section_html = _build_serp_section(soup, content_type, results, query)
        if section_html:
            sections.append(section_html)

    if not sections:
        return

    main = soup.find('main') or soup.find('body')
    if not main:
        return

    # Insert before random content blocks so SERP sections blend into the flow.
    # Exclude the footer so nothing lands after the page's closing element.
    content_blocks = ['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'table',
                      'blockquote', 'figure', 'section', 'div', 'aside']
    anchors = [
        c for c in main.find_all(content_blocks)
        if c.name not in ('footer', 'script', 'style')
        and len(c.get_text(strip=True)) > 0
    ]
    if not anchors:
        return

    random.shuffle(anchors)
    for section_html in sections:
        if not anchors:
            main.append(section_html)
            continue
        anchor = anchors.pop()
        anchor.insert_before(section_html)


def _build_serp_section(soup, content_type, results, query):
    """Build an HTML section for SERP content."""
    section = soup.new_tag('section', **{'class': 'serp-section my-8 p-6 rounded-lg shadow-lg'})

    title_tag = soup.new_tag('h2', **{'class': 'text-2xl font-bold mb-6'})
    title_text = _generate_section_title(content_type, query)
    title_tag.string = title_text
    section.append(title_tag)

    if content_type == 'news':
        items = results.get('news_results', [])[:4]
        for item in items:
            link_url = item.get('highlight', {}).get('link') or item.get('link')
            if not link_url:
                continue
            _append_news_card(soup, section, item, link_url)

    elif content_type == 'videos':
        items = [v for v in results.get('video_results', []) if v.get('link')][:3]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-3 gap-4'})
        for item in items:
            _append_video_card(soup, container, item)
        section.append(container)

    elif content_type == 'shopping':
        items = [p for p in results.get('shopping_results', []) if p.get('product_link')][:3]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-3 gap-6'})
        for item in items:
            _append_product_card(soup, container, item)
        section.append(container)

    elif content_type == 'jobs':
        items = results.get('jobs_results', [])[:3]
        for item in items:
            _append_job_card(soup, section, item)

    elif content_type == 'recipes':
        items = results.get('recipes_results', [])[:3]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-3 gap-4'})
        for item in items:
            _append_recipe_card(soup, container, item)
        section.append(container)

    elif content_type == 'books':
        items = results.get('books_results', [])[:3]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-3 gap-4'})
        for item in items:
            _append_book_card(soup, container, item)
        section.append(container)

    elif content_type == 'movies':
        items = results.get('showtimes', [])[:3]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-3 gap-4'})
        for item in items:
            _append_movie_card(soup, container, item)
        section.append(container)

    elif content_type == 'events':
        items = results.get('events_results', [])[:3]
        for item in items:
            _append_event_card(soup, section, item)

    elif content_type == 'local':
        items = [p for p in results.get('local_results', []) if p.get('place_id') or p.get('title')][:3]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-3 gap-4'})
        for item in items:
            _append_local_card(soup, container, item)
        section.append(container)

    elif content_type == 'related_questions':
        items = results.get('related_questions', [])[:4]
        for item in items:
            _append_related_question(soup, section, item)

    elif content_type == 'scholar':
        items = results.get('organic_results', [])[:3]
        for item in items:
            _append_scholar_card(soup, section, item)

    return section


def _generate_section_title(content_type, query):
    words = query.split()[:3]
    topic = ' '.join(w.capitalize() for w in words) if words else "Related"

    patterns = {
        'news': [f"Latest on {topic}", f"{topic} Headlines", f"What's New in {topic}"],
        'videos': [f"Watch: {topic}", f"{topic} in Action", f"Explore {topic}"],
        'shopping': [f"Shop {topic}", f"Top {topic} Picks", f"{topic} Essentials"],
        'jobs': [f"Open Roles: {topic}", f"{topic} Jobs", f"Now Hiring: {topic}"],
        'recipes': [f"Recipes for {topic}", f"Cook: {topic}", f"{topic} Dishes"],
        'books': [f"Books on {topic}", f"Read: {topic}", f"{topic} in Print"],
        'movies': [f"Now Showing: {topic}", f"{topic} on the Big Screen", f"Movie Times: {topic}"],
        'events': [f"Events: {topic}", f"Upcoming {topic}", f"{topic} Happenings"],
        'local': [f"Nearby: {topic}", f"Local {topic}", f"{topic} in Your Area"],
        'related_questions': [f"People Also Ask: {topic}", f"Questions About {topic}", f"{topic} FAQ"],
        'scholar': [f"Research: {topic}", f"Academic {topic}", f"{topic} Papers"],
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


def _append_job_card(soup, parent, item):
    a = soup.new_tag('a', href=item.get('link') or '#', target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline mb-4'})
    div = soup.new_tag('div', **{'class': 'p-4 rounded-lg border border-gray-200 hover:shadow-md transition-all'})
    h4 = soup.new_tag('h4', **{'class': 'font-semibold mb-1'})
    h4.string = item.get('title', 'Untitled Job')
    div.append(h4)
    if item.get('company_name'):
        p = soup.new_tag('p', **{'class': 'text-sm font-medium opacity-80'})
        p.string = item['company_name']
        div.append(p)
    if item.get('description'):
        p = soup.new_tag('p', **{'class': 'text-xs opacity-70 mt-1'})
        p.string = item['description'][:200]
        div.append(p)
    a.append(div)
    parent.append(a)


def _append_recipe_card(soup, parent, item):
    a = soup.new_tag('a', href=item.get('link') or '#', target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline'})
    div = soup.new_tag('div', **{'class': 'rounded-lg overflow-hidden border border-gray-200 shadow-sm hover:shadow-md transition-all'})
    if item.get('thumbnail'):
        img = soup.new_tag('img', src=item['thumbnail'], **{'class': 'w-full h-40 object-cover'})
        div.append(img)
    info = soup.new_tag('div', **{'class': 'p-3'})
    h4 = soup.new_tag('h4', **{'class': 'font-medium mb-1'})
    h4.string = item.get('title', 'Untitled Recipe')
    info.append(h4)
    if item.get('ingredients') or item.get('source'):
        p = soup.new_tag('p', **{'class': 'text-xs opacity-70'})
        p.string = item.get('source') or (', '.join(item.get('ingredients', [])[:4]))
        info.append(p)
    div.append(info)
    a.append(div)
    parent.append(a)


def _append_book_card(soup, parent, item):
    a = soup.new_tag('a', href=item.get('link') or '#', target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline'})
    div = soup.new_tag('div', **{'class': 'rounded-lg overflow-hidden border border-gray-200 shadow-sm hover:shadow-md transition-all'})
    if item.get('thumbnail'):
        img = soup.new_tag('img', src=item['thumbnail'], **{'class': 'w-full h-48 object-cover'})
        div.append(img)
    info = soup.new_tag('div', **{'class': 'p-3'})
    h4 = soup.new_tag('h4', **{'class': 'font-medium mb-1'})
    h4.string = item.get('title', 'Untitled Book')
    info.append(h4)
    if item.get('description'):
        p = soup.new_tag('p', **{'class': 'text-xs opacity-70'})
        p.string = item['description'][:160]
        info.append(p)
    div.append(info)
    a.append(div)
    parent.append(a)


def _append_movie_card(soup, parent, item):
    a = soup.new_tag('a', href=item.get('link') or '#', target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline'})
    div = soup.new_tag('div', **{'class': 'rounded-lg overflow-hidden border border-gray-200 shadow-sm hover:shadow-md transition-all'})
    if item.get('thumbnail'):
        img = soup.new_tag('img', src=item['thumbnail'], **{'class': 'w-full h-48 object-cover'})
        div.append(img)
    info = soup.new_tag('div', **{'class': 'p-3'})
    h4 = soup.new_tag('h4', **{'class': 'font-medium mb-1'})
    h4.string = item.get('title', 'Untitled Movie')
    info.append(h4)
    if item.get('theater'):
        p = soup.new_tag('p', **{'class': 'text-xs opacity-70'})
        p.string = f"At {item['theater']}"
        info.append(p)
    div.append(info)
    a.append(div)
    parent.append(a)


def _append_event_card(soup, parent, item):
    a = soup.new_tag('a', href=item.get('link') or '#', target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline mb-4'})
    div = soup.new_tag('div', **{'class': 'p-4 rounded-lg border border-gray-200 hover:shadow-md transition-all'})
    h4 = soup.new_tag('h4', **{'class': 'font-semibold mb-1'})
    h4.string = item.get('title', 'Untitled Event')
    div.append(h4)
    if item.get('date'):
        p = soup.new_tag('p', **{'class': 'text-sm font-medium opacity-80'})
        p.string = item['date']['when']
        div.append(p)
    if item.get('address'):
        p = soup.new_tag('p', **{'class': 'text-xs opacity-70 mt-1'})
        p.string = ', '.join([item['address'].get('venue') or '', item['address'].get('city') or '']).strip(', ')
        div.append(p)
    a.append(div)
    parent.append(a)


def _append_local_card(soup, parent, item):
    a = soup.new_tag('a', href=f"https://www.google.com/maps/place/?q=place_id:{item.get('place_id')}" if item.get('place_id') else '#',
                     target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline'})
    div = soup.new_tag('div', **{'class': 'p-4 rounded-lg border border-gray-200 hover:shadow-md transition-all'})
    h4 = soup.new_tag('h4', **{'class': 'font-medium mb-1'})
    h4.string = item.get('title', 'Untitled Place')
    div.append(h4)
    if item.get('rating'):
        p = soup.new_tag('p', **{'class': 'text-sm opacity-80'})
        p.string = f"Rating: {item['rating']} ({item.get('reviews')} reviews)"
        div.append(p)
    if item.get('address'):
        p = soup.new_tag('p', **{'class': 'text-xs opacity-70 mt-1'})
        p.string = item['address']
        div.append(p)
    a.append(div)
    parent.append(a)


def _append_related_question(soup, parent, item):
    details = soup.new_tag('details', **{'class': 'mb-2 rounded-lg border border-gray-200'})
    summary = soup.new_tag('summary', **{'class': 'px-4 py-3 font-medium cursor-pointer'})
    summary.string = item.get('question', 'Related question')
    details.append(summary)
    if item.get('answer'):
        div = soup.new_tag('div', **{'class': 'px-4 py-3 text-sm opacity-80'})
        div.append(BeautifulSoup(item['answer'], 'html.parser'))
        details.append(div)
    parent.append(details)


def _append_scholar_card(soup, parent, item):
    a = soup.new_tag('a', href=item.get('link') or '#', target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline mb-4'})
    div = soup.new_tag('div', **{'class': 'p-4 rounded-lg border border-gray-200 hover:shadow-md transition-all'})
    h4 = soup.new_tag('h4', **{'class': 'font-medium mb-1'})
    h4.string = item.get('title', 'Untitled Paper')
    div.append(h4)
    if item.get('publication_info', {}).get('summary'):
        p = soup.new_tag('p', **{'class': 'text-xs opacity-70'})
        p.string = item['publication_info']['summary']
        div.append(p)
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
