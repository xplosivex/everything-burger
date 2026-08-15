import random
import logging
from app.ai import complete
from app.generation.effects import _get_style_instructions

logger = logging.getLogger(__name__)

CONTENT_SYSTEM_PROMPT_TEMPLATE = """You are a chaotic, creative web content generator. You make pages
that are FUN to skim -- not essays to study. Think "weird internet energy" meets "someone
had too much fun building this." Every page should make someone laugh, raise an eyebrow,
or screenshot it to send to a friend.

=== FORMAT ===

Write ONE complete, flowing piece in the format of a **{ARCHETYPE_NAME}**.

{ARCHETYPE_STYLE}

=== TWISTS ===

This page has the following twists. Commit to them throughout:
{TWISTS}

=== OUTPUT FORMAT ===

Use these markers. Mix and match freely. NOT EVERY MARKER NEEDS TO APPEAR.

TITLE: [funny, dramatic, or absurd page title]
SUBTITLE: [punchy one-liner or tagline]

IMAGE: [3-5 word description for image search]
CAPTION: [funny or descriptive caption]
(include about {IMAGE_COUNT} images placed naturally throughout the page)

HEADING: [section heading]
PARAGRAPH: [short, punchy paragraph -- 2-3 sentences max]
LIST: [title]
- [item]
- [item]
NUMBEREDLIST: [title]
1. [item]
2. [item]
QUOTE: [text]
SOURCE: [attribution]
TABLE: [optional table]

RULES:
- Write ONE flowing piece in the chosen format -- not a stack of disconnected sections
- Keep paragraphs SHORT: 2-3 sentences max, not 5-6
- Be funny, weird, confident, and entertaining
- Invent fake statistics, quotes, testimonials, and facts with total conviction
- Reference earlier content in later parts. Reuse names, callback to jokes, escalate the absurdity
- DO NOT write HTML tags -- just plaintext with the markers above
- DO NOT write CSS or styling instructions
- Match explicit content if input is explicit
- Never create content harmful to minors
- Expand upon any outlandish or nonsensical themes
- The tone should lean comedic/absurd unless the input is clearly serious
"""


def generate_content(prompt: str, active_effects: list, temperature: float = 0.85,
                     archetype: dict = None, image_count: int = 3) -> str:
    """Stage 1: Generate entertaining, varied content from the user's prompt."""

    if archetype is None:
        from app.generation.archetypes import select_archetype
        archetype = select_archetype()

    from app.generation.archetypes import select_twists, build_element_content
    twists = select_twists()

    system = CONTENT_SYSTEM_PROMPT_TEMPLATE.replace('{ARCHETYPE_NAME}', archetype['name'])
    system = system.replace('{ARCHETYPE_STYLE}', archetype['content_style'])
    system = system.replace('{TWISTS}', '\n'.join('- ' + t for t in twists))
    system = system.replace('{IMAGE_COUNT}', str(image_count))

    elements = build_element_content(archetype.get('params', {}).get('elements', []))
    if elements:
        system = system.replace('=== OUTPUT FORMAT ===', f'{elements}\n\n=== OUTPUT FORMAT ===')

    # Check for style effects
    style_effect = next(
        (e for e in active_effects if e.effect_type == 'generation_style'), None
    )
    if style_effect:
        style_instructions = _get_style_instructions(style_effect.effect_value)
        if style_instructions:
            system = style_instructions + "\n\n" + system

    # Flavor injections -- push the model toward different vibes each time
    flavor_angles = [
        "Include a completely unhinged fake testimonial.",
        "Add a dramatic WARNING box about something absurd.",
        "Include a fake poll with ridiculous answer options.",
        "Add made-up statistics that sound just real enough to be funny.",
        "Include a fake breaking news alert.",
        "Add a ranking/top list with spicy hot takes.",
        "Include a ridiculous fake advertisement.",
        "Add a timeline of fictional events.",
        "Include a DEBATE section with two opposing absurd takes.",
        "Add comparison content that's unexpected.",
        "Include a conspiracy-theory-style fun fact.",
        "Add fake expert quotes from people with ridiculous job titles.",
        "Include a fake error message or loading screen.",
        "Add a choose-your-own-adventure moment.",
        "Include a fake dictionary entry for a made-up word.",
        "Add a nature-documentary-style field guide entry.",
        "Include a fake coupon or promotional offer.",
        "Include a mic-drop one-liner.",
        "Add a before-and-after comparison.",
        "Include a fake flowchart decision tree.",
        "Add a rant that escalates hilariously.",
        "Include a scoreboard or leaderboard.",
    ]
    selected_flavors = random.sample(flavor_angles, k=random.randint(2, 4))

    enhanced_prompt = f"""Create a fun, skimmable page about: {prompt}

Your angle/premise for this page (pick ONE and commit to it throughout):
Think of a specific funny take, framing, or "bit" for this topic. Not just "here's stuff about [topic]"
but "what if [topic] was [unexpected angle]" -- then make every part of the page serve that premise.

Make sure to include:
{chr(10).join('- ' + f for f in selected_flavors)}

CRITICAL: The page should feel like ONE flowing piece in the chosen format. Reference earlier content
in later parts. Reuse character names, callback to jokes, escalate the absurdity."""

    content = complete(
        'content',
        [
            {"role": "system", "content": system},
            {"role": "user", "content": enhanced_prompt}
        ],
        max_tokens=4000,
        temperature=temperature,
        top_p=0.92
    )
    logger.info(f"Stage 1 produced {len(content)} chars of content")
    return content
