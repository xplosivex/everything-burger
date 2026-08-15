import logging
from app.ai import complete

logger = logging.getLogger(__name__)

STYLING_SYSTEM_PROMPT = """You are a Tailwind CSS expert who makes FUN, visually diverse web pages.
Style the provided HTML using ONLY Tailwind utility classes.

BLOCK-SPECIFIC STYLING (make each block type look DIFFERENT):

=== STAPLE / PLAIN BLOCKS ===
- p, .content-paragraph -> readable, comfortable spacing, slightly larger text
- .content-list -> card background, styled bullets, padded
- .numbered-list -> large bold numbers, card items
- .content-table -> striped rows, rounded, shadow, colored header
- .heading-text -> large heading with accent underline, body text below
- .callout-box -> colored left border, padded, accent background
- .divider-text -> centered, decorative, muted color, spacing above/below
- .bold-statement -> text-2xl or text-3xl, centered, font-bold, accent color
- .caption-block -> small text, italic, bordered, museum-placard feel
- .summary-box -> card with header bar, padded content
- .key-value -> alternating row backgrounds, label bold, value normal
- blockquote -> large italic text, decorative left border

=== COMMON BLOCKS ===
- .funfact -> bright accent background, rounded, padded, tilted feel
- .warning-box -> red/orange/yellow background, bold border, dramatic
- .ranking -> large bold numbers, card-style items
- .testimonial -> italic text, decorative quote marks, subtle background
- .poll -> card with radio buttons, interactive feel, bordered
- .debate -> two-column layout (flex/grid), contrasting colors
- .tips -> clean list with bullets, card background
- .comparison -> side-by-side or highlighted box
- .timeline -> vertical line with dots, staggered entries
- .breaking-news -> bold red banner, all-caps, dramatic urgency
- .fake-ad -> cheesy bright background, rounded, "click here" energy
- .stats -> large bold numbers, grid layout, eye-catching
- .sidebar -> offset background, smaller text, border-left accent
- .hot-take -> fire emoji, bold, attention-grabbing background
- .unpopular-opinion -> split layout for opinion vs defense
- .overheard -> chat bubble styling, alternating alignment
- .review-card -> star display, card layout, footer
- .complaint-card -> angry red accents, letter feel
- .confession -> dark background, anonymous feel
- .rant -> escalating text size or intensity
- .mic-drop -> huge centered text, dramatic spacing
- .tier-list -> colored rows (S=gold, A=green, B=blue, C=orange, F=red)
- .pros-cons -> two-column green/red with verdict banner
- .checklist -> checkbox styling, card background
- .starter-pack -> grid of items, meme-style
- .do-dont -> two-column green DO / red DONT
- .superlatives -> award-ribbon styling, gold accents
- .scale-meter -> visual meter, colored gradient
- .matchup -> fight-card styling, versus divider
- .spectrum -> horizontal bar with markers, gradient
- .flowchart -> boxes connected by arrows, decision-tree look
- .before-after -> split screen, left/right comparison
- .scoreboard -> leaderboard table, medal colors for top 3
- .disclaimer -> tiny text, bordered box, legal feel
- .fake-loading -> progress bar, monospace, tech feel
- .error-message -> red/dark background, monospace, crash screen
- .notification -> phone notification card, rounded, shadow
- .news-ticker -> horizontal scroll, red/dark banner
- .psa -> official-looking, bordered, serious-tone card
- .update-banner -> yellow/orange highlight, editorial feel
- .spoiler, .secret -> clickable details/summary, styled toggle
- .quiz -> card with options, interactive feel
- .fill-in-blank -> inline input fields in text
- .choose-adventure -> option cards in grid, hover effects
- .progress-widget -> styled progress bar with label
- .fake-comments -> avatars (initials), comment bubbles, thread
- .fake-search -> search input with dropdown, Google-like
- .achievement-unlocked -> game popup, gold/trophy, celebration
- .fake-recipe -> recipe card, ingredients sidebar, numbered steps
- .haiku -> centered, whitespace, elegant minimal
- .faq -> clean accordion style
- .this-or-that -> two large option cards, "VS" in middle
- .rating-breakdown -> horizontal score bars, category labels

=== EXOTIC BLOCKS ===
- .alignment-chart -> 3x3 grid with colored cells, D&D aesthetic
- .bingo-card -> grid layout, bordered cells, fun backgrounds
- .classified-doc -> black/dark background, green/white monospace, redaction bars
- .prophecy -> dark/mystical background, ornate text, centered
- .wanted-poster -> old western style, sepia tones, bold WANTED
- .award-card -> certificate style, gold accents, formal
- .dictionary-entry -> serif font feel, structured definition
- .field-guide -> nature encyclopedia, bordered specimen card
- .dating-profile -> app card, profile layout, swipe energy
- .horoscope -> mystical/zodiac, purple/dark blues, stars
- .equation -> monospace, centered, chalkboard feel
- .transcript -> screenplay format, bold speakers, indented
- .coupon -> dashed border, tear-off style, bold discount
- .postcard -> rounded, slight tilt, handwriting font feel
- .footnote -> small text, numbered, offset
- .obituary -> newspaper obituary, bordered, solemn-but-funny
- .court-ruling -> legal document, serif, official seal feel
- .autopsy-report -> clinical, monospace, form-field styling
- .text-chain -> iMessage/SMS bubbles, blue/gray, timestamps
- .yelp-review -> Yelp red, star display, helpful count
- .weather-report -> weather card, icons, forecast grid
- .resume -> CV styling, sections, clean professional
- .product-recall -> official notice, red header, urgent
- .police-report -> form fields, monospace, incident styling
- .mad-lib -> paragraph with highlighted input blanks
- .stock-ticker -> financial display, green/red arrows, monospace numbers
- .conspiracy -> corkboard brown, red string connections, pinned notes feel
- .survival-guide -> field manual, olive/military colors, numbered steps
- .infomercial -> TV-style, bright yellow/red, "CALL NOW" energy
- .yearbook -> yearbook page, school colors, portrait-style layout
- .loading-story -> progress bar with narrative stages
- .complaint-form -> official form fields, pre-filled, bureaucratic
- .wiki-vandal -> Wikipedia styling with obvious red edit marks
- .email-chain -> threaded emails, indented replies, gray backgrounds
- .instruction-manual -> technical manual, diagrams feel, numbered sections

GENERAL RULES:
1. Add Tailwind classes to EVERY element
2. Use vibrant, varied colors -- each block should have its OWN color scheme
3. The page should look like a fun magazine/blog, NOT a corporate report
4. Make it responsive (sm:, md:, lg: breakpoints)
5. Use rounded corners, shadows, and spacing generously
6. Add the Tailwind CDN: <script src="https://cdn.tailwindcss.com"></script>
7. Give the body a colorful background -- NOT white, NOT gray
8. Vary section widths -- not everything should be full-width

PAGE FLOW STYLING (these make the page feel CONNECTED, not just stacked):
- .transition -> text-center, italic, text-gray-500/400, my-2, text-sm or text-base.
  These are the connective phrases between blocks. They should feel like gentle
  nudges, NOT like their own big content blocks. Subtle and small.
- .content-cluster -> group related blocks with a shared subtle background or
  left border accent. Use p-4 or p-6 with rounded-lg and a very light background
  to visually group 2-3 blocks without making them feel boxed in.
- hr.section-break -> styled as a decorative divider. NOT a plain gray line.
  Use a fun pattern: a row of emojis, a gradient line, a dashed colorful border,
  or a styled hr with custom color. Should feel intentional and designed.
- .page-closer -> the final 1-2 blocks. Give them extra emphasis: larger text,
  a distinctive background color, or a "finale" feel. The reader should sense
  "this is the ending."
- header -> should feel like a cohesive opening unit. Title, subtitle, and any
  opening content should share a background or visual treatment that groups them
  as the "intro." Think magazine cover or blog hero section.

CRITICAL:
- DO NOT remove any content, text, images, or HTML elements
- DO NOT add inline CSS or <style> tags -- Tailwind classes only
- DO NOT add explanations -- output ONLY the styled HTML
- The goal is a page that's FUN TO LOOK AT and fun to skim
"""



def apply_styling(html: str) -> str:
    """Stage 3: Apply Tailwind CSS styling to the HTML."""

    styled = complete(
        'styling',
        [
            {"role": "system", "content": STYLING_SYSTEM_PROMPT},
            {"role": "user", "content": html}
        ],
        max_tokens=12000,
        temperature=0.4,
        top_p=0.95
    )
    logger.info(f"Stage 3 produced {len(styled)} chars of styled HTML")
    return styled
