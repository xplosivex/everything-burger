import logging
from app.ai import complete

logger = logging.getLogger(__name__)

STRUCTURE_SYSTEM_PROMPT = """You convert structured plaintext content into ONE cohesive, semantic HTML5
document. The input uses content markers -- map each to semantic HTML so the page reads as a single
flowing artifact, NOT a stack of disconnected boxed sections.

=== FORMAT ===

Build ONE complete HTML5 document in the style of a **{ARCHETYPE_NAME}**.

{ARCHETYPE_LAYOUT}

=== INPUT MARKER -> HTML MAPPING ===

TITLE -> <h1> in <header>
SUBTITLE -> <p class="subtitle"> in <header>
IMAGE/CAPTION -> <figure> with <img> (src="placeholder.jpg", alt from description) and <figcaption>
HEADING -> <h2>
PARAGRAPH -> <p>
LIST -> <ul> with <li> items
NUMBEREDLIST -> <ol> with <li> items
QUOTE/SOURCE -> <blockquote> with <cite>
TABLE -> <table> with <thead>/<tbody>

=== DOCUMENT STRUCTURE ===

1. Complete HTML5 document: <!DOCTYPE html>, <html lang="en">, <head>, <body>
2. <head> must include meta charset, viewport, and <title>
3. Wrap everything in <main> with <header> at top and <footer> at bottom
4. Content flows as ONE document per the archetype layout -- columns, TOC, centered poster, etc.

CRITICAL RULES:
- Preserve EVERY IMAGE: marker as an <img> tag with src="placeholder.jpg" and alt text from the description
- Include at least one <ul> or <ol> somewhere in the document
- Preserve ALL content text exactly as provided
- DO NOT add CSS or styling -- just semantic HTML with descriptive class names
- Output raw HTML only -- no explanations
"""


def build_html_structure(content: str, archetype: dict = None, modifiers: list = None) -> str:
    """Stage 2: Convert structured text content into a single semantic HTML5 document."""

    if archetype is None:
        from app.generation.archetypes import select_archetype
        archetype = select_archetype()
    if modifiers is None:
        modifiers = []

    from app.generation.archetypes import build_element_html
    elements = build_element_html(archetype.get('params', {}).get('elements', []))

    system = STRUCTURE_SYSTEM_PROMPT.replace('{ARCHETYPE_NAME}', archetype['name'])
    system = system.replace('{ARCHETYPE_LAYOUT}', archetype['layout'])
    if elements:
        system = system.replace('=== DOCUMENT STRUCTURE ===', f'{elements}\n\n=== DOCUMENT STRUCTURE ===')
    if modifiers:
        modifier_section = '=== MODIFIERS (apply these to the document) ===\n' + '\n'.join(f'- {m}' for m in modifiers) + '\n=== END MODIFIERS ==='
        system = system.replace('=== DOCUMENT STRUCTURE ===', f'{modifier_section}\n\n=== DOCUMENT STRUCTURE ===')

    html = complete(
        'structure',
        [
            {"role": "system", "content": system},
            {"role": "user", "content": content}
        ],
        max_tokens=18000,
        temperature=0.3,
        top_p=0.95
    )
    logger.info(f"Stage 2 produced {len(html)} chars of HTML")
    return html
