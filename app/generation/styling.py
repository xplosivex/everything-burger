import logging
from app.ai import complete

logger = logging.getLogger(__name__)

STYLING_SYSTEM_PROMPT = """You are a world-class visual designer and Tailwind CSS expert. Your job is to make
the provided HTML look like a stunning, hand-crafted artifact -- NOT a generic web page.
Style it using ONLY Tailwind utility classes.

=== FORMAT ===

Apply ONE bold, cohesive visual identity to the whole page in the style of a **{ARCHETYPE_NAME}**.

{ARCHETYPE_THEME}

{ARCHETYPE_VISUAL}

=== VISUAL IDENTITY RULES ===

1. ONE unmistakable look: a single background treatment, one accent palette, one font pairing,
   and a clear typographic hierarchy. The page must be instantly recognizable as its format.
2. Make it RICH, not bland. Use at least 4 of these techniques across the page:
   - Textured or patterned backgrounds (gradients, radial glows, repeating patterns via
     background-image utilities, noise via layered gradients)
   - Decorative borders and frames (double borders, corner accents, dashed/ornate rules)
   - Ornamental dividers between sections (styled <hr>, emoji rows, gradient lines)
   - Distinctive typography (display fonts, letter-spacing, drop shadows, text gradients)
   - Cards, plaques, or frames with depth (shadows, rings, inset borders, tilt)
   - Hover/transition flourishes on interactive elements
   - Stamps, seals, badges, or ribbons as accent elements
   - Asymmetric or editorial layouts (offset columns, overlapping elements, rotated accents)
3. Differentiate content TYPOGRAPHICALLY and with subtle container treatments -- NOT with
   a rainbow of unrelated colored boxes. Every element should feel part of the same design.
4. Style any .serp-section elements to match the theme so injected content blends in seamlessly.
5. Add the Tailwind CDN: <script src="https://cdn.tailwindcss.com"></script>
6. Make it responsive (sm:, md:, lg: breakpoints).
7. The page should look like a single designed artifact that someone would screenshot and share.

CRITICAL:
- DO NOT remove any content, text, images, or HTML elements
- DO NOT add inline CSS or <style> tags -- Tailwind classes only
- DO NOT add explanations -- output ONLY the styled HTML
- The goal is a page that's FUN TO LOOK AT and fun to skim
"""


def apply_styling(html: str, archetype: dict = None, modifiers: list = None) -> str:
    """Stage 3: Apply one unified Tailwind theme to the HTML."""

    if archetype is None:
        from app.generation.archetypes import select_archetype
        archetype = select_archetype()
    if modifiers is None:
        modifiers = []

    from app.generation.archetypes import build_element_style
    elements = build_element_style(archetype.get('params', {}).get('elements', []))

    system = STYLING_SYSTEM_PROMPT.replace('{ARCHETYPE_NAME}', archetype['name'])
    system = system.replace('{ARCHETYPE_THEME}', archetype['theme'])
    system = system.replace('{ARCHETYPE_VISUAL}', archetype.get('visual_style', ''))
    if elements:
        system = system.replace('=== VISUAL IDENTITY RULES ===', f'{elements}\n\n=== VISUAL IDENTITY RULES ===')
    if modifiers:
        modifier_section = '=== MODIFIERS (style these into the page) ===\n' + '\n'.join(f'- {m}' for m in modifiers) + '\n=== END MODIFIERS ==='
        system = system.replace('=== VISUAL IDENTITY RULES ===', f'{modifier_section}\n\n=== VISUAL IDENTITY RULES ===')

    styled = complete(
        'styling',
        [
            {"role": "system", "content": system},
            {"role": "user", "content": html}
        ],
        max_tokens=16000,
        temperature=0.4,
        top_p=0.95
    )
    logger.info(f"Stage 3 produced {len(styled)} chars of styled HTML")
    return styled
