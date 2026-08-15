import re
import random
import logging
from bs4 import BeautifulSoup
from app.models import Item, db
from app.config import SERP_API_KEY
from app.generation.content import generate_content
from app.generation.structure import build_html_structure
from app.generation.styling import apply_styling
from app.generation.archetypes import select_archetype, get_archetype, select_twists, select_modifiers
from app.generation.images import fetch_all_images
from app.generation.serp import generate_search_queries, inject_serp_sections
from app.generation.effects import apply_effects
from app.generation.achievements import check_generation_achievements, award_generation_rewards

logger = logging.getLogger(__name__)

def get_prompt_length(user_id):
    length = 175
    has_keyboard = db.session.query(Item).filter(
        Item.user_id == user_id,
        Item.name == "Terrys Keyboard"
    ).first() is not None
    if has_keyboard:
        length += 50
    for effect in Item.get_active_effects(user_id):
        if effect.effect_type == 'prompt_length':
            length += int(float(effect.effect_value))
    return length

def generate_html_optimized(prompt: str, user_id: int, archetype_key: str = None,
                            seed_text: str = None, award: bool = True) -> str:
    # Gather active effects
    active_effects = Item.get_active_effects(user_id)

    # Calculate temperature from effects
    temperature = 0.85
    for effect in active_effects:
        if effect.effect_type == 'randomness':
            temperature = min(0.95, temperature * float(effect.effect_value))

    # Adjust image count from effects
    image_multiplier = 1
    for effect in active_effects:
        if effect.effect_type == 'image_count':
            image_multiplier *= float(effect.effect_value)

    # Pick this generation's archetype (or reuse a stored one for iterations),
    # plus fresh twists and modifiers
    if archetype_key:
        archetype = get_archetype(archetype_key)
    else:
        archetype = select_archetype()
    twists = select_twists()
    modifiers = select_modifiers()
    logger.info(f"Archetype: {archetype['name']}, twists: {twists}, modifiers: {modifiers}")

    # Base image count from the archetype's range (default 2-4), multiplied by the image_count item effect
    params = archetype.get('params', {})
    lo, hi = params.get('image_count', (2, 4))
    image_count = random.randint(lo, hi)
    if image_multiplier > 1:
        image_count = int(image_count * image_multiplier)

    # Nerd stats: everything that was randomly chosen for this generation
    from app.generation.archetypes import element_description
    selected_elements = archetype['params']['elements']
    meta = {
        'archetype': archetype['name'],
        'archetype_key': archetype['key'],
        'twists': twists,
        'modifiers': modifiers,
        'elements': [e['name'] for e in selected_elements],
        'element_descriptions': {e['name']: element_description(e) for e in selected_elements},
        'element_pool_size': archetype.get('element_pool_size', len(archetype['params']['elements'])),
        'image_count': image_count,
        'image_range': [lo, hi],
        'temperature': round(temperature, 2),
        'image_multiplier': image_multiplier,
        'seed': bool(seed_text),
    }

    # -- STAGE 1: Content Generation --
    logger.info("=== Stage 1: Generating content ===")
    content = generate_content(prompt, active_effects, temperature, archetype, image_count, seed_text)

    # Validate content was actually produced
    if len(content) < 150:
        logger.warning(f"Stage 1 produced only {len(content)} chars, retrying...")
        content = generate_content(prompt, active_effects, temperature=0.9, archetype=archetype,
                                   image_count=image_count, seed_text=seed_text)

    # -- STAGE 2: HTML Structure --
    logger.info("=== Stage 2: Building HTML structure ===")

    raw_html = build_html_structure(content, archetype, modifiers)

    # -- IMAGE FETCHING --
    logger.info("=== Fetching images ===")
    soup = BeautifulSoup(raw_html, 'html.parser')
    num_images = fetch_all_images(soup)
    raw_html = str(soup)

    # -- SERP ENRICHMENT (optional: requires a SerpAPI key) --
    if SERP_API_KEY:
        logger.info("=== Injecting SERP content ===")
        search_queries = generate_search_queries(raw_html)
        soup = BeautifulSoup(raw_html, 'html.parser')
        inject_serp_sections(soup, search_queries)
        raw_html = str(soup)
    else:
        logger.info("=== Skipping SERP enrichment (no SerpAPI key) ===")

    # -- STAGE 3: Styling --
    logger.info("=== Stage 3: Applying Tailwind styling ===")
    styled_html = apply_styling(raw_html, archetype, modifiers)

    # -- POST-PROCESSING --
    logger.info("=== Post-processing: effects, rewards, achievements ===")
    soup = BeautifulSoup(styled_html, 'html.parser')

    # Apply item effects
    apply_effects(soup, active_effects, user_id)

    # Ensure Tailwind CDN is present
    head = soup.find('head')
    if head and not soup.find('script', src=re.compile(r'tailwindcss')):
        head.append(soup.new_tag('script', src="https://cdn.tailwindcss.com"))

    final_html = str(soup.find('html') or soup)

    # Award rewards (skipped for iterations, which grant their own XP/crumbs)
    if award:
        award_generation_rewards(user_id, final_html)
        check_generation_achievements(soup, user_id, prompt, num_images)

    logger.info(f"=== Generation complete: {len(final_html)} chars ===")
    return final_html, archetype['key'], meta

