import json
import os
import random
import logging

logger = logging.getLogger(__name__)

_ARCHETYPE_DIR = os.path.join(os.path.dirname(__file__), 'archetypes')
_NON_ARCHETYPE_FILES = {'twists.json', 'modifiers.json'}


def _load_archetypes() -> dict:
    """Load all archetype definitions from the archetypes/ JSON directory."""
    archetypes = {}
    for filename in sorted(os.listdir(_ARCHETYPE_DIR)):
        if not filename.endswith('.json'):
            continue
        if filename in _NON_ARCHETYPE_FILES:
            continue
        key = filename[:-5]
        with open(os.path.join(_ARCHETYPE_DIR, filename), 'r', encoding='utf-8') as f:
            archetypes[key] = json.load(f)
    return archetypes


def _load_list(filename: str) -> list:
    """Load a JSON list (twists/modifiers) from the archetypes/ directory."""
    with open(os.path.join(_ARCHETYPE_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)


ARCHETYPES = _load_archetypes()
TWISTS = _load_list('twists.json')
MODIFIERS = _load_list('modifiers.json')


def build_element_content(elements: list) -> str:
    """Build the selected-elements section for the content prompt."""
    if not elements:
        return ''
    lines = ['=== SELECTED ELEMENTS (these MUST appear on this page) ===']
    for el in elements:
        lines.append(el['content'])
    lines.append('=== END SELECTED ELEMENTS ===')
    return '\n'.join(lines)


def build_element_html(elements: list) -> str:
    """Build the selected-elements section for the structure prompt."""
    if not elements:
        return ''
    lines = ['=== SELECTED ELEMENTS (these MUST be built in the document) ===']
    for el in elements:
        lines.append(f'- {el["html"]}')
    lines.append('=== END SELECTED ELEMENTS ===')
    return '\n'.join(lines)


def build_element_style(elements: list) -> str:
    """Build the selected-elements section for the styling prompt."""
    if not elements:
        return ''
    lines = ['=== SELECTED ELEMENTS (style these to match the theme) ===']
    for el in elements:
        lines.append(f'- {el["style"]}')
    lines.append('=== END SELECTED ELEMENTS ===')
    return '\n'.join(lines)


def select_archetype() -> dict:
    """Pick a random archetype and resolve one random variant of its pools."""
    archetype = random.choice(list(ARCHETYPES.values()))
    pool = archetype['elements']
    count = random.randint(3, min(9, len(pool)))
    resolved = {
        'name': archetype['name'],
        'content_style': random.choice(archetype['content_styles']),
        'layout': random.choice(archetype['layouts']),
        'theme': random.choice(archetype['themes']),
        'params': {
            'image_count': random.choice(archetype['image_ranges']),
            'elements': random.sample(pool, k=count),
        },
    }
    logger.info(f"Selected archetype: {resolved['name']} ({count} elements)")
    return resolved


def select_twists() -> list:
    """Pick 1-2 random twists to inject into the content prompt."""
    count = random.randint(1, 2)
    twists = random.sample(TWISTS, k=count)
    logger.info(f"Selected twists: {twists}")
    return twists


def select_modifiers() -> list:
    """Pick 1-3 random modifiers (weighted: 1 most common, 3 rarest)."""
    count = random.choices([1, 2, 3], weights=[50, 35, 15], k=1)[0]
    modifiers = random.sample(MODIFIERS, k=count)
    logger.info(f"Selected modifiers: {modifiers}")
    return modifiers
