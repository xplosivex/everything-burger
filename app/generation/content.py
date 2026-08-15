import random
import logging
from app.ai import complete
from app.generation.palette import select_block_palette, build_block_prompt_section
from app.generation.effects import _get_style_instructions

logger = logging.getLogger(__name__)

CONTENT_SYSTEM_PROMPT_TEMPLATE = """You are a chaotic, creative web content generator. You make pages
that are FUN to skim -- not essays to study. Think "weird internet energy" meets "someone
had too much fun building this." Every page should make someone laugh, raise an eyebrow,
or screenshot it to send to a friend.

=== PAGE NARRATIVE ARC ===

Every page tells a STORY, even if it's absurd. Think of it like a magazine article or a
comedy bit -- not a random bag of blocks dumped on a page. Structure your page like this:

OPENING (first 2-3 blocks): Hook the reader. Set the tone. Introduce the topic with
  energy. The title and subtitle do heavy lifting here, then a strong opening paragraph
  or section that establishes the "angle" -- the specific spin or premise you're taking
  on this topic.

MIDDLE (5-8 blocks): Build on the premise. Each block should REACT TO or BUILD ON what
  came before. A ranking should rank things mentioned earlier. A testimonial should quote
  someone responding to a claim you just made. A warning should warn about something the
  content just described. Stats should "prove" something you asserted. Use plain blocks
  (PARAGRAPH, LIST, etc.) as connective tissue BETWEEN the fun blocks -- a sentence that
  transitions, reacts, or sets up what's coming next.

CLOSER (2-3 blocks): Land the plane. Callback to something from the opening. End with
  something punchy -- a mic drop, a final verdict, a dramatic sign-off, a callback joke.
  The reader should feel like the page ENDED, not just stopped.

=== CRITICAL: MAKING BLOCKS FLOW TOGETHER ===

The #1 mistake is blocks that feel like isolated islands. AVOID THIS by:

- REFERENCING EARLIER CONTENT: If a section mentions "the legendary 1987 incident", a
  later testimonial should quote someone who was "there in '87". A warning should say
  "given what we just learned above..."

- RUNNING BITS: Introduce a character, concept, or joke early and bring it back. A fake
  expert quoted in paragraph 2 could show up again in a testimonial later. A made-up
  statistic could be "disproven" in a later debate block.

- TRANSITIONS: Between blocks, the last line of one block should set up the next. End a
  section with "But not everyone agrees..." before a DEBATE block. End a ranking with
  "Speaking of #1..." before diving deeper.

- SHARED VOCABULARY: Use the same funny names, made-up terms, and specific references
  across multiple blocks. If you invent "Dr. Crunchwhistle" in a quote, have them appear
  in a testimonial or complaint later.

- ESCALATION: The page should get progressively more unhinged. Start somewhat grounded
  and let the absurdity build. The last few blocks should be the wildest.

=== OUTPUT FORMAT ===

Use these markers. Mix and match freely. NOT EVERY MARKER NEEDS TO APPEAR.
Pick 10-16 blocks total.

TITLE: [funny, dramatic, or absurd page title]
SUBTITLE: [punchy one-liner or tagline]

IMAGE: [3-5 word description for image search]
CAPTION: [funny or descriptive caption]
(include 1-3 images placed naturally throughout the page)

{DYNAMIC_BLOCKS}

RULES:
- Use 10-16 content blocks per page -- variety over volume
- Keep paragraphs SHORT: 2-3 sentences max, not 5-6
- Be funny, weird, confident, and entertaining
- Invent fake statistics, quotes, testimonials, and facts with total conviction
- Every page should feel like ONE cohesive piece, not a collection of unrelated blocks
- DO NOT just write section after section of paragraphs -- MIX UP the block types
- Use plain blocks (PARAGRAPH, LIST, TABLE, etc.) as TRANSITIONS between fun blocks
- At least 5 different block types must appear on every page
- EVERY block should reference, react to, or build on something from another block
- DO NOT write HTML tags -- just plaintext with the markers above
- DO NOT write CSS or styling instructions
- Match explicit content if input is explicit
- Never create content harmful to minors
- Expand upon any outlandish or nonsensical themes
- The tone should lean comedic/absurd unless the input is clearly serious
"""



def generate_content(prompt: str, active_effects: list, temperature: float = 0.85) -> str:
    """Stage 1: Generate entertaining, varied content from the user's prompt."""

    # Select this generation's unique block palette
    palette = select_block_palette()
    dynamic_section = build_block_prompt_section(palette)
    system = CONTENT_SYSTEM_PROMPT_TEMPLATE.replace('{DYNAMIC_BLOCKS}', dynamic_section)

    # Log what exotics were picked (the interesting part)
    exotic_picks = [k for t, k in palette if t == 'exotic']
    logger.info(f"Exotic blocks this generation: {exotic_picks}")

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
but "what if [topic] was [unexpected angle]" -- then make every block serve that premise.

Make sure to include:
{chr(10).join('- ' + f for f in selected_flavors)}

CRITICAL: The blocks should feel like ONE flowing piece. Reference earlier content in later blocks.
Reuse character names, callback to jokes, escalate the absurdity. Transitions between blocks matter."""

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
