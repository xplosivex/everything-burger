import random
import logging
from collections import Counter
from app.generation.blocks import STAPLE_BLOCKS, COMMON_BLOCKS, EXOTIC_BLOCKS, BLOCK_CATEGORIES

logger = logging.getLogger(__name__)

def _weighted_sample(pool: dict, k: int, exclude: set = None) -> list:
    """
    Select k items from a block pool using weighted random sampling
    WITHOUT replacement. Returns list of block keys.
    """
    if exclude is None:
        exclude = set()

    candidates = [(key, block['weight']) for key, block in pool.items() if key not in exclude]
    if not candidates:
        return []

    k = min(k, len(candidates))
    keys, weights = zip(*candidates)
    selected = []

    # Weighted sampling without replacement
    keys = list(keys)
    weights = list(weights)
    for _ in range(k):
        if not keys:
            break
        total = sum(weights)
        probs = [w / total for w in weights]
        idx = random.choices(range(len(keys)), weights=probs, k=1)[0]
        selected.append(keys[idx])
        keys.pop(idx)
        weights.pop(idx)

    return selected


def _get_all_blocks_by_category(tier_pool: dict) -> dict:
    """Group block keys by category from a given tier pool."""
    by_cat = {}
    for key, block in tier_pool.items():
        cat = block['category']
        by_cat.setdefault(cat, []).append(key)
    return by_cat


def select_block_palette() -> list:
    """
    Build a unique block palette for this generation.

    Structure:
      1. Pick 3-5 STAPLE blocks (can include duplicates of the same type)
      2. Pick 4-7 COMMON blocks (no dupes, weighted, category-diverse)
      3. Pick 1-3 EXOTIC blocks (no dupes, weighted, rare surprises)

    Total target: 10-15 blocks per palette.

    Category diversity: at least one common/exotic pick comes from each
    category that has available blocks.
    """
    palette = []

    # --- STAPLES (allow duplicates) ---
    num_staples = random.randint(3, 5)
    staple_keys = list(STAPLE_BLOCKS.keys())
    staple_weights = [STAPLE_BLOCKS[k]['weight'] for k in staple_keys]

    for _ in range(num_staples):
        pick = random.choices(staple_keys, weights=staple_weights, k=1)[0]
        palette.append(('staple', pick))

    # --- COMMONS (no dupes, category-diverse) ---
    num_commons = random.randint(4, 7)
    used_common_keys = set()

    # Phase 1: one from each category that has common blocks
    common_by_cat = _get_all_blocks_by_category(COMMON_BLOCKS)
    for cat in BLOCK_CATEGORIES:
        cat_pool = common_by_cat.get(cat, [])
        if cat_pool:
            candidates = [(k, COMMON_BLOCKS[k]['weight']) for k in cat_pool]
            keys_c, weights_c = zip(*candidates)
            pick = random.choices(keys_c, weights=weights_c, k=1)[0]
            used_common_keys.add(pick)
            palette.append(('common', pick))

    # Phase 2: fill remaining common slots
    remaining_common = max(0, num_commons - len(used_common_keys))
    if remaining_common > 0:
        extra = _weighted_sample(COMMON_BLOCKS, remaining_common, exclude=used_common_keys)
        for k in extra:
            used_common_keys.add(k)
            palette.append(('common', k))

    # --- EXOTICS (no dupes, weighted) ---
    num_exotics = random.choices([1, 2, 3], weights=[40, 40, 20], k=1)[0]
    exotic_picks = _weighted_sample(EXOTIC_BLOCKS, num_exotics)
    for k in exotic_picks:
        palette.append(('exotic', k))

    # Shuffle the full palette so block order varies
    random.shuffle(palette)

    logger.info(
        f"Palette: {len(palette)} blocks "
        f"({sum(1 for t,_ in palette if t=='staple')} staple, "
        f"{sum(1 for t,_ in palette if t=='common')} common, "
        f"{sum(1 for t,_ in palette if t=='exotic')} exotic)"
    )

    return palette


def build_block_prompt_section(palette: list) -> str:
    """
    Build the content block instructions section of the system prompt
    from the selected palette.

    Handles duplicate staple keys by including the prompt text once
    with a note that multiple instances can be used.
    """
    all_pools = {**STAPLE_BLOCKS, **COMMON_BLOCKS, **EXOTIC_BLOCKS}

    # Count occurrences of each key
    from collections import Counter
    key_counts = Counter(key for _, key in palette)

    lines = ['=== CONTENT BLOCK TYPES (use these for this page) ===', '']

    seen = set()
    for _, key in palette:
        if key in seen:
            continue
        seen.add(key)

        block = all_pools[key]
        lines.append(block['prompt'])
        if key_counts[key] > 1:
            lines.append(f'(you may use this block type up to {key_counts[key]} times on this page)')
        lines.append('')

    lines.append('=== END BLOCK TYPES ===')
    return '\n'.join(lines)
