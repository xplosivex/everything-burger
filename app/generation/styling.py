import logging
from app.ai import complete

logger = logging.getLogger(__name__)

STYLING_SYSTEM_PROMPT = """You are a Tailwind CSS expert who makes FUN, visually cohesive web pages.
Style the provided HTML using ONLY Tailwind utility classes.

=== FORMAT ===

Apply ONE unified theme to the whole page in the style of a **{ARCHETYPE_NAME}**.

{ARCHETYPE_THEME}

=== THEME RULES ===

1. ONE unified look: a single background, one accent palette, one font pairing, and a clear
   typographic hierarchy for the whole page
2. Differentiate content TYPOGRAPHICALLY (headings, pull-quotes, lists, captions) -- NOT with
   different colored boxes per section
3. Style any .serp-section elements to match the theme so injected content blends in
4. Add the Tailwind CDN: <script src="https://cdn.tailwindcss.com"></script>
5. Make it responsive (sm:, md:, lg: breakpoints)
6. Use rounded corners, shadows, and spacing generously
7. The page should look like a single designed artifact, NOT a stack of random colored cards

CRITICAL:
- DO NOT remove any content, text, images, or HTML elements
- DO NOT add inline CSS or <style> tags -- Tailwind classes only
- DO NOT add explanations -- output ONLY the styled HTML
- The goal is a page that's FUN TO LOOK AT and fun to skim
"""


def apply_styling(html: str, archetype: dict = None) -> str:
    """Stage 3: Apply one unified Tailwind theme to the HTML."""

    if archetype is None:
        from app.generation.archetypes import select_archetype
        archetype = select_archetype()

    from app.generation.archetypes import build_element_style
    elements = build_element_style(archetype.get('params', {}).get('elements', []))

    system = STYLING_SYSTEM_PROMPT.replace('{ARCHETYPE_NAME}', archetype['name'])
    system = system.replace('{ARCHETYPE_THEME}', archetype['theme'])
    if elements:
        system = system.replace('=== THEME RULES ===', f'{elements}\n\n=== THEME RULES ===')

    styled = complete(
        'styling',
        [
            {"role": "system", "content": system},
            {"role": "user", "content": html}
        ],
        max_tokens=12000,
        temperature=0.4,
        top_p=0.95
    )
    logger.info(f"Stage 3 produced {len(styled)} chars of styled HTML")
    return styled
