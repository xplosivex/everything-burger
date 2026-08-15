import logging
from app.ai import complete

logger = logging.getLogger(__name__)

STRUCTURE_SYSTEM_PROMPT = """You convert structured plaintext content into semantic, varied HTML5.
The input uses content markers -- map each to a DISTINCT HTML pattern so the page feels visually
diverse, not like a wall of identical sections.

INPUT MARKER -> HTML MAPPING (use these, plus infer mappings for any unlisted markers):

=== CORE ===
TITLE -> <h1> in <header>
SUBTITLE -> <p class="subtitle"> in <header>
IMAGE/CAPTION -> <figure> with <img> (src="placeholder.jpg", alt from description) and <figcaption>

=== STAPLE / PLAIN ===
PARAGRAPH -> <p> or <div class="content-paragraph"> (standalone paragraph)
SECTION -> <section> with <h2> heading and <p> body
LIST -> <div class="content-list"> with <h3> title and <ul>
NUMBEREDLIST -> <div class="numbered-list"> with <h3> title and <ol>
TABLE -> <div class="content-table"> with <h3> title and <table>
HEADING/TEXT -> <div class="heading-text"> with <h2> and <p>
CALLOUT/CONTENT -> <div class="callout-box"> with emoji/label and text
DIVIDER -> <div class="divider-text"> centered decorative text
BOLD -> <div class="bold-statement"> large centered text
CAPTIONBLOCK -> <div class="caption-block"> small formatted text
SUMMARY/CONTENT -> <div class="summary-box"> with title and text
KEYVALUE -> <div class="key-value"> with <dl> definition list
BLOCKQUOTE/SOURCE -> <blockquote> with <cite>

=== COMMON ===
FUNFACT -> <aside class="funfact"> with lightbulb emoji and bold text
QUOTE/ATTRIBUTION -> <blockquote class="fancy-quote"> with <cite>
TESTIMONIAL/AUTHOR -> <div class="testimonial"> with <blockquote> and <footer>
DEBATE/COUNTERPOINT -> <div class="debate"> two opposing <div> blocks side by side
HOTTAKE -> <div class="hot-take"> bold, flame emoji
UNPOPULAROPINION/DEFENSE -> <div class="unpopular-opinion"> split layout
OVERHEARD -> <div class="overheard"> chat bubble styling
REVIEW/STARS/REVIEWER -> <div class="review-card"> star rating and quote
COMPLAINT/SIGNED -> <div class="complaint-card"> angry letter styling
CONFESSION -> <div class="confession"> anonymous post styling
RANT -> <div class="rant"> escalating text styling
MICDROP -> <div class="mic-drop"> large bold centered text, mic emoji
RANKING -> <div class="ranking"> with <ol>
TIPS -> <div class="tips"> with <ul>
STATS -> <div class="stats"> with stat items
TIERLIST -> <div class="tier-list"> colored tier rows
PROSCONS/VERDICT -> <div class="pros-cons"> two-column layout
CHECKLIST -> <div class="checklist"> checkbox inputs
STARTERPACK -> <div class="starter-pack"> grid of items
DODONT -> <div class="do-dont"> two-column do/don't layout
SUPERLATIVES -> <div class="superlatives"> award-style list
COMPARISON -> <div class="comparison"> side-by-side
TIMELINE -> <div class="timeline"> vertical timeline
POLL/OPTIONS -> <div class="poll"> radio buttons
SCALE/VERDICT -> <div class="scale-meter"> range element
MATCHUP/ROUNDS/CHAMPION -> <div class="matchup"> fight card styling
SPECTRUM -> <div class="spectrum"> horizontal bar with markers
FLOWCHART -> <div class="flowchart"> decision tree with arrows/connections
BEFOREAFTER/VERDICT -> <div class="before-after"> split comparison
SCOREBOARD -> <div class="scoreboard"> leaderboard table
WARNING -> <div class="warning-box"> bold border, warning emoji
BREAKING -> <div class="breaking-news"> red banner, alert emoji
AD -> <div class="fake-ad"> promotional callout
SIDEBAR -> <aside class="sidebar"> offset content
DISCLAIMER -> <div class="disclaimer"> small legal-style text
ERROR -> <div class="error-message"> crash screen styling
NOTIFICATION -> <div class="notification"> phone notification card
TICKER -> <div class="news-ticker"> scrolling <marquee> or container
LOADING/PERCENT -> <div class="fake-loading"> <progress> bar
PSA -> <div class="psa"> public service announcement box
UPDATE -> <div class="update-banner"> blog-style edit notice
SPOILER/CONTENT -> <details class="spoiler"> with <summary>
SECRET/REVEAL -> <details class="secret"> with <summary>
QUIZ/ANSWER -> <div class="quiz"> form with radio buttons and hidden answer
FILLIN/ANSWER -> <div class="fill-in-blank"> inputs in text
ADVENTURE/OPTIONS -> <div class="choose-adventure"> option cards
PROGRESS/PERCENT/NOTE -> <div class="progress-widget"> <progress> and label
COMMENTS -> <div class="fake-comments"> comment thread blocks
SEARCHBAR/SUGGESTIONS -> <div class="fake-search"> input with dropdown
ACHIEVEMENT -> <div class="achievement-unlocked"> game popup styling
RECIPE/INGREDIENTS/STEPS -> <div class="fake-recipe"> recipe card
HAIKU -> <div class="haiku"> centered, italicized
MARQUEE -> <marquee> with text
FAQ -> <div class="faq"> with <details>/<summary> Q&A
THISORTHAT -> <div class="this-or-that"> two option cards side by side
RATINGBREAKDOWN -> <div class="rating-breakdown"> category scores with bars

=== EXOTIC ===
ALIGNMENTCHART -> <div class="alignment-chart"> 3x3 grid table
BINGO -> <div class="bingo-card"> 3x3 grid table
CLASSIFIED/REDACTED -> <div class="classified-doc"> monospace, redaction bars
PROPHECY -> <div class="prophecy"> mystical/oracle styling
WANTED/CRIME/REWARD -> <div class="wanted-poster"> western poster styling
AWARD/RECIPIENT/REASON -> <div class="award-card"> certificate styling
DICTIONARY/PRONUNCIATION/DEFINITION/USAGE -> <div class="dictionary-entry"> dictionary page
FIELDGUIDE/SPECIES -> <div class="field-guide"> nature encyclopedia card
DATINGPROFILE/BIO -> <div class="dating-profile"> app profile card
HOROSCOPE/LUCKY_NUMBER -> <div class="horoscope"> mystical zodiac card
EQUATION/PROOF -> <div class="equation"> monospace math styling
TRANSCRIPT -> <div class="transcript"> screenplay format
COUPON/DISCOUNT/CODE/EXPIRES -> <div class="coupon"> tear-off coupon styling
POSTCARD/FROM/TO -> <div class="postcard"> postcard with handwriting feel
FOOTNOTE -> <div class="footnote"> small numbered reference
OBITUARY -> <div class="obituary"> memorial/newspaper obituary styling
COURTRULING -> <div class="court-ruling"> legal document styling
AUTOPSY -> <div class="autopsy-report"> clinical report styling
TEXTCHAIN -> <div class="text-chain"> iMessage/SMS bubble styling
YELPREVIEW -> <div class="yelp-review"> Yelp-style review card
WEATHER -> <div class="weather-report"> weather forecast card
RESUME -> <div class="resume"> resume/CV document styling
RECALL -> <div class="product-recall"> official recall notice styling
POLICEREPORT -> <div class="police-report"> incident report form styling
MADLIB -> <div class="mad-lib"> paragraph with input blanks
STOCKTICKER -> <div class="stock-ticker"> financial ticker display
CONSPIRACY -> <div class="conspiracy"> corkboard/red-string styling
SURVIVALGUIDE -> <div class="survival-guide"> field manual styling
INFOMERCIAL -> <div class="infomercial"> TV infomercial callout
YEARBOOK -> <div class="yearbook"> yearbook page styling
LOADINGSTORY -> <div class="loading-story"> animated progress narrative
COMPLAINTFORM -> <div class="complaint-form"> official form with fields
WIKIVANDAL -> <div class="wiki-vandal"> Wikipedia article with edit marks
EMAILCHAIN -> <div class="email-chain"> threaded email styling
MANUAL -> <div class="instruction-manual"> technical manual styling

DOCUMENT STRUCTURE:
1. Complete HTML5 document: <!DOCTYPE html>, <html lang="en">, <head>, <body>
2. <head> must include meta charset, viewport, and <title>
3. Wrap everything in <main> with <header> at top and <footer> at bottom
4. Each content block should be its own distinct HTML element

PAGE FLOW -- MAKING IT FEEL CONNECTED:
1. Add short <p class="transition"> elements between blocks when the content has a
   natural transition phrase (e.g. "But that's not all...", "Speaking of which...",
   "Now here's where it gets interesting..."). If the plaintext content has transition
   sentences, put them in these elements rather than inside the blocks themselves.
2. Group related blocks inside <div class="content-cluster"> containers when 2-3 blocks
   clearly relate to each other (e.g. a section followed by a testimonial reacting to it).
   This creates visual grouping without breaking individual block styling.
3. Use <hr class="section-break"> between major topic shifts to create intentional
   pacing, but NOT between every single block.
4. The <header> should feel like a magazine cover -- title, subtitle, and optionally
   the first image or a hook paragraph, all grouped together.
5. The last 1-2 blocks before <footer> should feel like a deliberate ending -- wrap
   them in <div class="page-closer"> to signal visual finality.

CRITICAL RULES:
- Every block type should produce VISUALLY DIFFERENT HTML structure
- DO NOT just wrap everything in <section><p> -- use the varied elements listed
- If you encounter a marker not listed above, infer appropriate HTML with a descriptive class name
- Preserve ALL content text exactly as provided
- DO NOT add CSS or styling -- just semantic HTML with descriptive class names
- Output raw HTML only -- no explanations
"""



def build_html_structure(content: str) -> str:
    """Stage 2: Convert structured text content into semantic HTML5."""

    html = complete(
        'structure',
        [
            {"role": "system", "content": STRUCTURE_SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ],
        max_tokens=7000,
        temperature=0.3,
        top_p=0.95
    )
    logger.info(f"Stage 2 produced {len(html)} chars of HTML")
    return html
