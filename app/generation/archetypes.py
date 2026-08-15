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


def _resolve(archetype: dict, key: str) -> dict:
    """Resolve one random variant of an archetype's pools."""
    pool = archetype['elements']
    count = random.randint(3, min(9, len(pool)))
    resolved = {
        'key': key,
        'name': archetype['name'],
        'content_style': random.choice(archetype['content_styles']),
        'layout': random.choice(archetype['layouts']),
        'theme': random.choice(archetype['themes']),
        'visual_style': archetype.get('visual_style', ''),
        'params': {
            'image_count': random.choice(archetype['image_ranges']),
            'elements': random.sample(pool, k=count),
        },
        'element_pool_size': len(pool),
    }
    return resolved


def select_archetype() -> dict:
    """Pick a random archetype and resolve one random variant of its pools."""
    key = random.choice(list(ARCHETYPES.keys()))
    resolved = _resolve(ARCHETYPES[key], key)
    logger.info(f"Selected archetype: {resolved['name']} ({len(resolved['params']['elements'])} elements)")
    return resolved


def get_archetype(key: str) -> dict:
    """Resolve a random variant of a specific archetype by its key."""
    if key not in ARCHETYPES:
        raise KeyError(f"Unknown archetype key: {key}")
    return _resolve(ARCHETYPES[key], key)


def random_archetype_key() -> str:
    """Pick a random archetype key (for backfilling pages without one)."""
    return random.choice(list(ARCHETYPES.keys()))


def element_description(element: dict) -> str:
    """Human-readable description of an element from its content fragment."""
    content = element.get('content', '')
    # Strip the marker prefix (e.g. 'SUPERLATIVES: [title]...') and brackets
    desc = content.split(':', 1)[-1] if ':' in content else content
    desc = desc.replace('[', '').replace(']', '').strip()
    if not desc:
        return element.get('name', '')
    return desc


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
