import random
import logging

logger = logging.getLogger(__name__)

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


# Each archetype carries POOLS of variants. select_archetype() resolves one
# random combination per generation, so the same archetype never produces the
# same content style + layout + theme + params twice.
ARCHETYPES = {
    'tabloid_newspaper': {
        'name': 'tabloid newspaper',
        'content_styles': [
            (
                "Write like a screaming tabloid front page. Shouty all-caps headlines, "
                "breathless EXCLUSIVE boxes, dramatic subheads, and a gossipy voice that "
                "treats the topic as the scandal of the century. Short punchy paragraphs, "
                "pull-quotes, and a 'sources say' energy throughout."
            ),
            (
                "Write like a sleazy celebrity gossip rag. A scandalous lead story, "
                "italicized 'insider' quotes, a 'you won't believe' framing, and a "
                "breathless voice that treats the topic as a celebrity meltdown. "
                "Short paragraphs, bold subheads, and a 'sources close to the topic' "
                "energy."
            ),
            (
                "Write like a supermarket checkout tabloid. A wild headline, a 'world "
                "exclusive' claim, numbered 'shocking facts', and a voice that is "
                "conspiratorial and thrilled. Every section should feel like it's one "
                "step from a UFO headline."
            ),
        ],
        'layouts': [
            (
                "Build a newspaper front page: a giant masthead header, a bold lead headline, "
                "multi-column body text (CSS columns), an EXCLUSIVE sidebar box, and a footer "
                "with a fake edition line. Content flows as one continuous article."
            ),
            (
                "Build a tabloid spread: a huge screaming headline, a lead image slot, "
                "two-column body text, a 'world exclusive' callout box, and a footer with "
                "a fake price and date. One continuous front page."
            ),
            (
                "Build a newspaper page: a masthead, a banner headline, a three-column "
                "body with a pull-quote box in the middle, a sidebar 'related scandal' "
                "box, and a footer. Flows as one article."
            ),
        ],
        'themes': [
            (
                "Newsprint look: off-white paper background, black serif headlines, red accent "
                "for EXCLUSIVE boxes, thin black rules between columns. One unified newspaper "
                "palette."
            ),
            (
                "Cheap tabloid look: bright yellow background, black bold headlines, red "
                "and blue accent boxes, a slightly grainy paper feel, and a bold sans-serif "
                "for headlines. Unified and loud."
            ),
            (
                "Retro newspaper look: cream paper, dark brown ink, a red masthead, "
                "serif body text, and thin column rules. Unified and vintage."
            ),
        ],
        'image_ranges': [(2, 4), (3, 5), (1, 3)],
        'elements': [
            {
                'name': 'exclusive_box',
                'content': "EXCLUSIVE: [a scandalous claim presented as a world exclusive]",
                'html': "EXCLUSIVE -> <div class=\"exclusive-box\"> with a bold red label and text",
                'style': ".exclusive-box -> red border, bold label, dramatic background",
            },
            {
                'name': 'screaming_headline',
                'content': "HEADLINE: [ALL-CAPS SHOUTY HEADLINE]",
                'html': "HEADLINE -> <h2 class=\"screaming-headline\">",
                'style': ".screaming-headline -> huge bold uppercase text, red accent",
            },
            {
                'name': 'insider_quote',
                'content': "INSIDER: [quote from a 'source close to the topic']\nSOURCE: [anonymous insider]",
                'html': "INSIDER -> <blockquote class=\"insider-quote\"> with <cite>",
                'style': ".insider-quote -> italic, decorative quote marks, subtle background",
            },
            {
                'name': 'shocking_facts',
                'content': "SHOCKING: [title]\n- [shocking fact]\n- [shocking fact]\n- [shocking fact]",
                'html': "SHOCKING -> <div class=\"shocking-facts\"> with <h3> and <ul>",
                'style': ".shocking-facts -> numbered bold items, red numbers",
            },
            {
                'name': 'gossip_column',
                'content': "GOSSIP: [a paragraph of breathless gossip about the topic]",
                'html': "GOSSIP -> <div class=\"gossip-column\"> with <p>",
                'style': ".gossip-column -> italic text, dashed left border",
            },
            {
                'name': 'page_three',
                'content': "PAGETHREE: [a wild, slightly unhinged sidebar story]",
                'html': "PAGETHREE -> <aside class=\"page-three\"> with <p>",
                'style': ".page-three -> offset sidebar, bold border, loud background",
            },
            {
                'name': 'sources_say',
                'content': "SOURCESSAY: [a claim attributed to 'sources']",
                'html': "SOURCESSAY -> <p class=\"sources-say\">",
                'style': ".sources-say -> small caps, muted color, centered",
            },
            {
                'name': 'scandal_timeline',
                'content': "TIMELINE: [title]\n- [date]: [scandal beat]\n- [date]: [scandal beat]",
                'html': "TIMELINE -> <div class=\"scandal-timeline\"> with <h3> and <ul>",
                'style': ".scandal-timeline -> vertical line with dots, staggered entries",
            },
            {
                'name': 'you_wont_believe',
                'content': "WONTBELIEVE: [a 'you won't believe' teaser paragraph]",
                'html': "WONTBELIEVE -> <p class=\"wont-believe\">",
                'style': ".wont-believe -> bold, centered, dramatic spacing",
            },
            {
                'name': 'editorial_rant',
                'content': "RANT: [an escalating editorial rant about the topic]",
                'html': "RANT -> <div class=\"editorial-rant\"> with <p>",
                'style': ".editorial-rant -> escalating text size, angry red accents",
            },
            {
                'name': 'celebrity_angle',
                'content': "CELEB: [the topic framed as a celebrity story]",
                'html': "CELEB -> <div class=\"celebrity-angle\"> with <p>",
                'style': ".celebrity-angle -> gold accents, paparazzi feel",
            },
            {
                'name': 'poll_man_on_street',
                'content': "STREETPOLL: [title]\n- [option]: [percent]%\n- [option]: [percent]%",
                'html': "STREETPOLL -> <div class=\"street-poll\"> with <h3> and <ul>",
                'style': ".street-poll -> bar-style percentages, bold colors",
            },
            {
                'name': 'correction_box',
                'content': "CORRECTION: [a hilariously wrong 'correction' of a previous claim]",
                'html': "CORRECTION -> <div class=\"correction-box\"> with <p>",
                'style': ".correction-box -> small text, bordered, apologetic gray",
            },
            {
                'name': 'next_issue_teaser',
                'content': "NEXTISSUE: [a teaser for a 'next issue' story]",
                'html': "NEXTISSUE -> <p class=\"next-issue\">",
                'style': ".next-issue -> italic, centered, teaser styling",
            },
            {
                'name': 'price_tag',
                'content': "PRICE: [a fake cover price and edition line]",
                'html': "PRICE -> <p class=\"price-tag\">",
                'style': ".price-tag -> small, muted, footer feel",
            },
            {
                'name': 'banner_alert',
                'content': "BANNER: [a dramatic breaking banner claim]",
                'html': "BANNER -> <div class=\"banner-alert\"> with <p>",
                'style': ".banner-alert -> red banner, all-caps, urgent",
            },
        ],
    },
    'wiki_article': {
        'name': 'vandalized Wikipedia article',
        'content_styles': [
            (
                "Write like a Wikipedia article that has been vandalized. Neutral encyclopedic "
                "tone for the real content, but with obviously fake facts, 'citation needed' "
                "tags, and a few inserted absurd sentences that break the fourth wall."
            ),
            (
                "Write like a Wikipedia article mid-edit-war. Neutral encyclopedic prose "
                "interrupted by [citation needed], [who?], and [dubious] tags, plus a "
                "recurring anonymous editor inserting increasingly unhinged claims."
            ),
            (
                "Write like a Wikipedia article that has been 'improved' by someone who "
                "clearly has no idea what the topic is. Confident encyclopedic tone, "
                "wildly wrong facts, and a 'this article needs cleanup' banner energy."
            ),
        ],
        'layouts': [
            (
                "Build a single-column Wikipedia-style article: a title header, a small infobox "
                "table, a table of contents, numbered sections with headings, and a references "
                "list at the bottom. One continuous document."
            ),
            (
                "Build a Wikipedia article: a title header, a 'this article has issues' "
                "banner box, an infobox table, a table of contents, sections with headings, "
                "and a references list. One continuous document."
            ),
            (
                "Build a wiki page: a title header, a short lead paragraph, an infobox, "
                "numbered sections, a 'talk page' note box, and a references footer. "
                "Single column, continuous."
            ),
        ],
        'themes': [
            (
                "Wikipedia look: white background, blue link-colored accents, serif body text, "
                "a light gray infobox, and a subtle 'edit' red for the vandalism. Unified and "
                "clean."
            ),
            (
                "Wikipedia dark-mode look: dark gray background, light text, blue links, "
                "a dark infobox, and red 'edit' accents. Unified and modern."
            ),
            (
                "Classic wiki look: white background, black text, blue links, a bordered "
                "infobox, and a yellow 'issues' banner. Unified and familiar."
            ),
        ],
        'image_ranges': [(1, 3), (2, 4), (0, 2)],
        'elements': [
            {
                'name': 'infobox',
                'content': "INFOBOX: [title]\n- [field]: [value]\n- [field]: [value]",
                'html': "INFOBOX -> <table class=\"infobox\"> with <tbody> of key/value rows",
                'style': ".infobox -> light gray box, bordered, small text, right-aligned",
            },
            {
                'name': 'citation_needed',
                'content': "CITATIONNEEDED: [a claim that obviously needs a citation]",
                'html': "CITATIONNEEDED -> <p> with <span class=\"citation-needed\">[citation needed]</span>",
                'style': ".citation-needed -> small red superscript tag",
            },
            {
                'name': 'table_of_contents',
                'content': "TOC: [title]\n- [section 1]\n- [section 2]\n- [section 3]",
                'html': "TOC -> <nav class=\"toc\"> with <h3> and <ul>",
                'style': ".toc -> bordered box, numbered links, small text",
            },
            {
                'name': 'vandalism_note',
                'content': "VANDAL: [an obviously vandalized sentence inserted into the article]",
                'html': "VANDAL -> <p class=\"vandalism\">",
                'style': ".vandalism -> red text, strikethrough accents",
            },
            {
                'name': 'edit_war',
                'content': "EDITWAR: [a section where two editors argue in the article text]",
                'html': "EDITWAR -> <div class=\"edit-war\"> with two opposing <p> blocks",
                'style': ".edit-war -> two-column, contrasting colors",
            },
            {
                'name': 'disambiguation',
                'content': "DISAMBIG: [a 'this article is about X, for other uses see Y' note]",
                'html': "DISAMBIG -> <p class=\"disambiguation\">",
                'style': ".disambiguation -> small italic text, gray background",
            },
            {
                'name': 'references',
                'content': "REFERENCES: [title]\n- [fake source 1]\n- [fake source 2]",
                'html': "REFERENCES -> <div class=\"references\"> with <h3> and <ol>",
                'style': ".references -> small text, numbered, muted",
            },
            {
                'name': 'cleanup_banner',
                'content': "CLEANUP: [a 'this article needs cleanup' banner message]",
                'html': "CLEANUP -> <div class=\"cleanup-banner\"> with <p>",
                'style': ".cleanup-banner -> yellow banner, bordered, warning feel",
            },
            {
                'name': 'see_also',
                'content': "SEEALSO: [title]\n- [related fake article]\n- [related fake article]",
                'html': "SEEALSO -> <div class=\"see-also\"> with <h3> and <ul>",
                'style': ".see-also -> small text, blue links, bordered",
            },
            {
                'name': 'talk_page',
                'content': "TALK: [a talk page comment about the article]",
                'html': "TALK -> <div class=\"talk-page\"> with <p>",
                'style': ".talk-page -> indented, gray background, comment feel",
            },
            {
                'name': 'stub_notice',
                'content': "STUB: [a 'this article is a stub' notice]",
                'html': "STUB -> <p class=\"stub-notice\">",
                'style': ".stub-notice -> small centered text, muted",
            },
            {
                'name': 'wikilinks',
                'content': "WIKILINK: [a sentence with fake blue-linked terms]",
                'html': "WIKILINK -> <p> with <a class=\"wikilink\"> terms",
                'style': ".wikilink -> blue underlined links",
            },
            {
                'name': 'external_links',
                'content': "EXTLINKS: [title]\n- [fake external link]\n- [fake external link]",
                'html': "EXTLINKS -> <div class=\"external-links\"> with <h3> and <ul>",
                'style': ".external-links -> small text, blue links, bordered",
            },
            {
                'name': 'category_tags',
                'content': "CATEGORIES: [title]\n- [fake category]\n- [fake category]",
                'html': "CATEGORIES -> <div class=\"category-tags\"> with <ul>",
                'style': ".category-tags -> small gray tags, bottom of page",
            },
            {
                'name': 'lead_paragraph',
                'content': "LEAD: [a neutral encyclopedic lead paragraph]",
                'html': "LEAD -> <p class=\"lead-paragraph\">",
                'style': ".lead-paragraph -> larger first paragraph, serif",
            },
            {
                'name': 'history_section',
                'content': "HISTORY: [a 'history' section with absurd fake events]",
                'html': "HISTORY -> <section class=\"history-section\"> with <h2> and <p>",
                'style': ".history-section -> standard section, serif headings",
            },
        ],
    },
    'wanted_poster': {
        'name': 'wanted poster',
        'content_styles': [
            (
                "Write like an Old West wanted poster. A dramatic description of the 'criminal' "
                "(the topic), a list of alleged crimes, a reward amount, and a stern warning. "
                "Voice is authoritative, dramatic, and slightly absurd."
            ),
            (
                "Write like a modern FBI wanted poster. A 'most wanted' framing, a "
                "description of the 'fugitive' (the topic), aliases, known associates, "
                "and a 'do not approach' warning. Voice is clinical and dramatic."
            ),
            (
                "Write like a pirate-era wanted notice. A dramatic description of the "
                "'scoundrel' (the topic), a list of crimes against the crown, a bounty, "
                "and a warning about the scoundrel's tricks. Voice is theatrical and "
                "slightly unhinged."
            ),
        ],
        'layouts': [
            (
                "Build a centered poster: a huge WANTED title, a large image slot, a description "
                "block, a bulleted list of crimes, a reward line, and a footer warning. Everything "
                "centered on one page like a printed poster."
            ),
            (
                "Build a wanted poster: a big WANTED header, a portrait image slot, "
                "a description, a 'known aliases' list, a reward box, and a footer "
                "warning. Centered, poster-style."
            ),
            (
                "Build a notice: a WANTED banner, an image slot, a description, a "
                "numbered list of crimes, a reward line, and a 'contact' footer. "
                "One centered document."
            ),
        ],
        'themes': [
            (
                "Sepia Old West look: aged paper background, dark brown text, a bold black WANTED "
                "header, thin double borders, and a vintage serif font. One unified sepia palette."
            ),
            (
                "Faded poster look: pale yellow paper, dark ink, a red WANTED stamp, "
                "rough borders, and a distressed vintage feel. Unified and weathered."
            ),
            (
                "Modern FBI look: white background, black text, a red 'MOST WANTED' "
                "banner, a photo frame, and a clean sans-serif. Unified and official."
            ),
        ],
        'image_ranges': [(1, 2), (1, 3), (0, 1)],
        'elements': [
            {
                'name': 'crimes_list',
                'content': "CRIMES: [title]\n- [crime]\n- [crime]\n- [crime]",
                'html': "CRIMES -> <div class=\"crimes-list\"> with <h3> and <ul>",
                'style': ".crimes-list -> bulleted, bold crime names, sepia tones",
            },
            {
                'name': 'reward_box',
                'content': "REWARD: [a dramatic reward amount]",
                'html': "REWARD -> <div class=\"reward-box\"> with <p>",
                'style': ".reward-box -> bold centered text, double border",
            },
            {
                'name': 'description',
                'content': "DESCRIPTION: [a dramatic physical description of the 'criminal']",
                'html': "DESCRIPTION -> <p class=\"poster-description\">",
                'style': ".poster-description -> serif, centered, aged paper feel",
            },
            {
                'name': 'aliases',
                'content': "ALIASES: [title]\n- [alias]\n- [alias]",
                'html': "ALIASES -> <div class=\"aliases\"> with <h3> and <ul>",
                'style': ".aliases -> small text, bordered, centered",
            },
            {
                'name': 'warning',
                'content': "WARNING: [a stern 'do not approach' warning]",
                'html': "WARNING -> <div class=\"poster-warning\"> with <p>",
                'style': ".poster-warning -> bold, red or black, bordered",
            },
            {
                'name': 'last_seen',
                'content': "LASTSEEN: [a 'last seen' location and date]",
                'html': "LASTSEEN -> <p class=\"last-seen\">",
                'style': ".last-seen -> small text, centered, muted",
            },
            {
                'name': 'contact_line',
                'content': "CONTACT: [a 'contact the sheriff' line]",
                'html': "CONTACT -> <p class=\"contact-line\">",
                'style': ".contact-line -> small caps, centered, footer feel",
            },
            {
                'name': 'known_associates',
                'content': "ASSOCIATES: [title]\n- [associate]\n- [associate]",
                'html': "ASSOCIATES -> <div class=\"known-associates\"> with <h3> and <ul>",
                'style': ".known-associates -> bordered list, small text",
            },
            {
                'name': 'bounty_stamp',
                'content': "STAMP: [a dramatic 'BOUNTY' stamp line]",
                'html': "STAMP -> <p class=\"bounty-stamp\">",
                'style': ".bounty-stamp -> rotated red stamp text, bold",
            },
            {
                'name': 'poster_number',
                'content': "POSTERNUM: [a fake poster serial number]",
                'html': "POSTERNUM -> <p class=\"poster-number\">",
                'style': ".poster-number -> tiny monospace text, corner placement",
            },
            {
                'name': 'sheriff_note',
                'content': "SHERIFF: [a note from the 'sheriff' about the criminal]",
                'html': "SHERIFF -> <blockquote class=\"sheriff-note\"> with <cite>",
                'style': ".sheriff-note -> italic, bordered, official feel",
            },
            {
                'name': 'reward_terms',
                'content': "TERMS: [the absurd terms of the reward]",
                'html': "TERMS -> <p class=\"reward-terms\">",
                'style': ".reward-terms -> small text, muted, legal feel",
            },
        ],
    },
    'game_manual': {
        'name': 'retro game manual',
        'content_styles': [
            (
                "Write like a retro video game instruction manual. Numbered sections, dramatic "
                "WARNING boxes, 'DO NOT' instructions, controller diagrams described in text, "
                "and an over-earnest voice explaining the topic as if it were a game mechanic."
            ),
            (
                "Write like a 90s game manual written by someone who has never played the "
                "game. Over-excited descriptions of 'features', numbered controls, a "
                "story section, and a 'tips from the pros' section. Voice is earnest "
                "and wrong."
            ),
            (
                "Write like a strategy guide for a game that doesn't exist. Numbered "
                "walkthrough steps, 'pro tip' boxes, a secrets section, and a voice "
                "that treats the topic as a game to be beaten."
            ),
        ],
        'layouts': [
            (
                "Build a manual: a cover header, numbered sections with headings, WARNING callout "
                "boxes, a diagram area (image slots), and a back-cover blurb. Flows as one "
                "document with clear section breaks."
            ),
            (
                "Build a manual: a cover page header, a 'how to play' section, numbered "
                "controls, a story section, a WARNING box, and a tips section. One "
                "continuous document."
            ),
            (
                "Build a strategy guide: a cover header, numbered walkthrough sections, "
                "pro tip boxes, a secrets list, and a back-cover blurb. Flows as one "
                "document."
            ),
        ],
        'themes': [
            (
                "Retro manual look: dark navy background, neon accent colors (cyan/magenta), "
                "bold blocky headings, yellow WARNING boxes. One unified arcade palette."
            ),
            (
                "16-bit manual look: dark background, bright primary accents, pixel-style "
                "headings, bordered boxes, and a chunky feel. Unified and retro."
            ),
            (
                "Strategy guide look: white background, blue headings, green 'pro tip' "
                "boxes, and a clean sans-serif. Unified and helpful."
            ),
        ],
        'image_ranges': [(2, 4), (3, 5), (1, 3)],
        'elements': [
            {
                'name': 'controls',
                'content': "CONTROLS: [title]\n- [button]: [action]\n- [button]: [action]",
                'html': "CONTROLS -> <div class=\"controls\"> with <h3> and <ul>",
                'style': ".controls -> bordered box, button-style items, neon accents",
            },
            {
                'name': 'warning_box',
                'content': "WARNING: [a dramatic 'DO NOT' warning]",
                'html': "WARNING -> <div class=\"manual-warning\"> with <p>",
                'style': ".manual-warning -> yellow box, bold border, warning icon",
            },
            {
                'name': 'story_section',
                'content': "STORY: [the 'story' of the game, absurdly epic]",
                'html': "STORY -> <section class=\"game-story\"> with <h2> and <p>",
                'style': ".game-story -> dramatic heading, atmospheric text",
            },
            {
                'name': 'pro_tip',
                'content': "PROTIP: [a 'pro tip' for playing]",
                'html': "PROTIP -> <div class=\"pro-tip\"> with <p>",
                'style': ".pro-tip -> green box, lightbulb icon, bordered",
            },
            {
                'name': 'secrets',
                'content': "SECRETS: [title]\n- [secret]\n- [secret]",
                'html': "SECRETS -> <div class=\"secrets\"> with <h3> and <ul>",
                'style': ".secrets -> hidden-feel box, dashed border, mystery styling",
            },
            {
                'name': 'level_guide',
                'content': "LEVEL: [a numbered level walkthrough]",
                'html': "LEVEL -> <div class=\"level-guide\"> with <h3> and <ol>",
                'style': ".level-guide -> numbered steps, bold level numbers",
            },
            {
                'name': 'health_bar',
                'content': "HEALTH: [a description of the topic's 'health' or stats]",
                'html': "HEALTH -> <div class=\"health-bar\"> with <p>",
                'style': ".health-bar -> progress-bar feel, green/red",
            },
            {
                'name': 'back_cover',
                'content': "BACKCOVER: [a back-cover blurb selling the game]",
                'html': "BACKCOVER -> <div class=\"back-cover\"> with <p>",
                'style': ".back-cover -> bold, centered, dramatic",
            },
            {
                'name': 'cheat_codes',
                'content': "CHEATS: [title]\n- [code]: [effect]\n- [code]: [effect]",
                'html': "CHEATS -> <div class=\"cheat-codes\"> with <h3> and <ul>",
                'style': ".cheat-codes -> monospace codes, bordered, secret feel",
            },
            {
                'name': 'multiplayer',
                'content': "MULTIPLAYER: [a 'multiplayer' section about the topic]",
                'html': "MULTIPLAYER -> <section class=\"multiplayer\"> with <h2> and <p>",
                'style': ".multiplayer -> two-player feel, split accent colors",
            },
            {
                'name': 'difficulty',
                'content': "DIFFICULTY: [a difficulty rating for the topic]",
                'html': "DIFFICULTY -> <p class=\"difficulty\">",
                'style': ".difficulty -> star or skull rating, bold",
            },
            {
                'name': 'manual_index',
                'content': "INDEX: [title]\n- [section]: [page]\n- [section]: [page]",
                'html': "INDEX -> <div class=\"manual-index\"> with <h3> and <ul>",
                'style': ".manual-index -> two-column, dotted leaders, small text",
            },
            {
                'name': 'safety_note',
                'content': "SAFETY: [an absurd safety warning about the topic]",
                'html': "SAFETY -> <div class=\"safety-note\"> with <p>",
                'style': ".safety-note -> bordered, small text, official feel",
            },
            {
                'name': 'game_over',
                'content': "GAMEOVER: [a dramatic 'game over' closer]",
                'html': "GAMEOVER -> <p class=\"game-over\">",
                'style': ".game-over -> huge bold text, centered, dramatic",
            },
            {
                'name': 'high_score',
                'content': "HIGHSCORE: [a fake high score table]",
                'html': "HIGHSCORE -> <table class=\"high-score\"> with <thead>/<tbody>",
                'style': ".high-score -> arcade table, bold scores, neon",
            },
            {
                'name': 'insert_coin',
                'content': "INSERTCOIN: [a 'insert coin to continue' line]",
                'html': "INSERTCOIN -> <p class=\"insert-coin\">",
                'style': ".insert-coin -> blinking-feel text, centered, arcade",
            },
        ],
    },
    'museum_exhibit': {
        'name': 'museum exhibit',
        'content_styles': [
            (
                "Write like museum exhibit placards. Formal, hushed, educational tone describing "
                "the topic as a historical artifact. Each section is a placard with a title, "
                "description, and a 'specimen' detail line."
            ),
            (
                "Write like a natural history museum guide. Each section is a 'specimen "
                "card' with a scientific-sounding name, a description, a habitat line, "
                "and a 'fun fact'. Voice is educational and quietly amused."
            ),
            (
                "Write like a modern art museum placard. Pretentious, interpretive, and "
                "absurdly deep about the topic. Each section is a placard with a title, "
                "an 'artist statement', and a 'medium' line."
            ),
        ],
        'layouts': [
            (
                "Build a gallery: a museum header, then a series of placard cards each with a "
                "title, an image slot, a description, and a small caption. Arranged in a clean "
                "grid or single column with generous spacing."
            ),
            (
                "Build a museum wing: a header, a floor-plan note, then specimen cards "
                "each with an image slot, a name, a description, and a detail line. "
                "Grid layout, one continuous exhibit."
            ),
            (
                "Build an exhibit: a header, a 'gallery guide' intro, then numbered "
                "placards with image slots and captions. One continuous walkthrough."
            ),
        ],
        'themes': [
            (
                "Museum look: warm off-white walls, dark charcoal text, gold accent borders, "
                "serif headings, and a subtle 'exhibit number' label on each placard. Unified "
                "and elegant."
            ),
            (
                "Natural history look: cream background, forest green accents, specimen "
                "cards with thin borders, and a serif font. Unified and scholarly."
            ),
            (
                "Modern art look: white walls, black text, a single bold accent color, "
                "minimal placards, and lots of whitespace. Unified and gallery-clean."
            ),
        ],
        'image_ranges': [(3, 5), (4, 6), (2, 4)],
        'elements': [
            {
                'name': 'placard',
                'content': "PLACARD: [title]\n[description of the 'artifact']",
                'html': "PLACARD -> <div class=\"placard\"> with <h3> and <p>",
                'style': ".placard -> bordered card, gold accent, serif",
            },
            {
                'name': 'specimen_card',
                'content': "SPECIMEN: [name]\n[description]\nHABITAT: [fake habitat]",
                'html': "SPECIMEN -> <div class=\"specimen-card\"> with <h3>, <p>, and a detail line",
                'style': ".specimen-card -> bordered, scientific label, green accent",
            },
            {
                'name': 'exhibit_number',
                'content': "EXHIBITNUM: [a fake exhibit number and wing]",
                'html': "EXHIBITNUM -> <p class=\"exhibit-number\">",
                'style': ".exhibit-number -> small caps, muted, museum label feel",
            },
            {
                'name': 'curator_note',
                'content': "CURATOR: [a note from the 'curator']",
                'html': "CURATOR -> <blockquote class=\"curator-note\"> with <cite>",
                'style': ".curator-note -> italic, bordered, gold accent",
            },
            {
                'name': 'gallery_caption',
                'content': "CAPTION: [a caption for an exhibit image]",
                'html': "CAPTION -> <figcaption class=\"gallery-caption\">",
                'style': ".gallery-caption -> small italic text, muted",
            },
            {
                'name': 'fun_fact',
                'content': "FUNFACT: [a 'did you know' museum fact]",
                'html': "FUNFACT -> <aside class=\"fun-fact\"> with <p>",
                'style': ".fun-fact -> lightbulb icon, subtle background, rounded",
            },
            {
                'name': 'donor_plaque',
                'content': "DONOR: [a fake donor plaque]",
                'html': "DONOR -> <p class=\"donor-plaque\">",
                'style': ".donor-plaque -> small centered text, gold, formal",
            },
            {
                'name': 'floor_plan',
                'content': "FLOORPLAN: [a description of the exhibit layout]",
                'html': "FLOORPLAN -> <p class=\"floor-plan\">",
                'style': ".floor-plan -> small text, dashed border, map feel",
            },
            {
                'name': 'audio_guide',
                'content': "AUDIO: [a 'press play for audio guide' transcript]",
                'html': "AUDIO -> <div class=\"audio-guide\"> with <p>",
                'style': ".audio-guide -> italic, bordered, play-button feel",
            },
            {
                'name': 'restoration_note',
                'content': "RESTORATION: [a note about the 'restoration' of the artifact]",
                'html': "RESTORATION -> <p class=\"restoration-note\">",
                'style': ".restoration-note -> small text, muted, technical",
            },
            {
                'name': 'gift_shop',
                'content': "GIFTSHOP: [a 'available in the gift shop' line]",
                'html': "GIFTSHOP -> <p class=\"gift-shop\">",
                'style': ".gift-shop -> small italic text, playful",
            },
            {
                'name': 'temporary_exhibit',
                'content': "TEMPORARY: [a 'temporary exhibit' banner]",
                'html': "TEMPORARY -> <div class=\"temporary-exhibit\"> with <p>",
                'style': ".temporary-exhibit -> colored banner, bordered, notice feel",
            },
            {
                'name': 'provenance',
                'content': "PROVENANCE: [a fake provenance history of the artifact]",
                'html': "PROVENANCE -> <p class=\"provenance\">",
                'style': ".provenance -> small text, muted, archival feel",
            },
            {
                'name': 'interactive_station',
                'content': "INTERACTIVE: [a 'please touch' interactive station description]",
                'html': "INTERACTIVE -> <div class=\"interactive-station\"> with <p>",
                'style': ".interactive-station -> bordered, playful, hands-on feel",
            },
        ],
    },
    'conspiracy_corkboard': {
        'name': 'conspiracy corkboard',
        'content_styles': [
            (
                "Write like a conspiracy theorist's corkboard. Scattered notes, red-string "
                "connections, paranoid observations, 'they don't want you to know' framing, "
                "and photos with handwritten captions. Voice is urgent and unhinged."
            ),
            (
                "Write like a paranoid researcher's notes. Handwritten-feel observations, "
                "cross-references to other notes, 'I've been watching' framing, and a "
                "voice that is increasingly convinced. Each section is a pinned note."
            ),
            (
                "Write like a whistleblower's leaked document. Redacted lines, urgent "
                "warnings, 'they will delete this' framing, and a voice that is "
                "breathless and terrified. Each section is a classified note."
            ),
        ],
        'layouts': [
            (
                "Build a corkboard: a brown background with pinned note cards scattered at "
                "slight rotations, image slots as 'photos', and connecting lines implied by "
                "the layout. Notes flow as one chaotic but connected board."
            ),
            (
                "Build a corkboard: pinned notes in a loose grid, each slightly rotated, "
                "with photo slots, red-string accent lines, and a 'case file' header. "
                "One connected board."
            ),
            (
                "Build a case file: a 'TOP SECRET' header, then pinned note sections "
                "with photo slots and redacted lines. Flows as one paranoid document."
            ),
        ],
        'themes': [
            (
                "Corkboard look: brown cork background, cream paper notes with slight rotation, "
                "red string accents, marker-style handwriting fonts, and pushpin dots. One "
                "unified conspiracy palette."
            ),
            (
                "Case file look: manila folder background, black text, red 'CONFIDENTIAL' "
                "stamps, and a typewriter font. Unified and bureaucratic."
            ),
            (
                "Dark web look: near-black background, green monospace text, redacted "
                "red bars, and a terminal feel. Unified and ominous."
            ),
        ],
        'image_ranges': [(3, 5), (2, 4), (4, 6)],
        'elements': [
            {
                'name': 'pinned_note',
                'content': "NOTE: [a handwritten-feel paranoid observation]",
                'html': "NOTE -> <div class=\"pinned-note\"> with <p>",
                'style': ".pinned-note -> cream paper, slight rotation, pushpin dot",
            },
            {
                'name': 'red_string',
                'content': "REDSTRING: [a connection between two 'clues']",
                'html': "REDSTRING -> <p class=\"red-string\">",
                'style': ".red-string -> red text, connecting-line feel",
            },
            {
                'name': 'photo_caption',
                'content': "PHOTO: [a 'photo' description with a paranoid caption]",
                'html': "PHOTO -> <figure class=\"conspiracy-photo\"> with <img> and <figcaption>",
                'style': ".conspiracy-photo -> polaroid frame, slight rotation",
            },
            {
                'name': 'classified_doc',
                'content': "CLASSIFIED: [a redacted classified document excerpt]",
                'html': "CLASSIFIED -> <div class=\"classified-doc\"> with <p>",
                'style': ".classified-doc -> monospace, redaction bars, dark background",
            },
            {
                'name': 'they_dont_want',
                'content': "THEYDONT: [a 'they don't want you to know' claim]",
                'html': "THEYDONT -> <p class=\"they-dont\">",
                'style': ".they-dont -> bold, urgent, red accent",
            },
            {
                'name': 'witness_account',
                'content': "WITNESS: [a 'witness' account of the conspiracy]",
                'html': "WITNESS -> <blockquote class=\"witness-account\"> with <cite>",
                'style': ".witness-account -> italic, bordered, handwritten feel",
            },
            {
                'name': 'timeline_of_events',
                'content': "EVENTS: [title]\n- [date]: [suspicious event]\n- [date]: [suspicious event]",
                'html': "EVENTS -> <div class=\"event-timeline\"> with <h3> and <ul>",
                'style': ".event-timeline -> vertical line, red dots, staggered",
            },
            {
                'name': 'symbol_analysis',
                'content': "SYMBOL: [an analysis of a 'hidden symbol']",
                'html': "SYMBOL -> <div class=\"symbol-analysis\"> with <p>",
                'style': ".symbol-analysis -> bordered, diagram feel, red circles",
            },
            {
                'name': 'leaked_memo',
                'content': "MEMO: [a leaked internal memo]",
                'html': "MEMO -> <div class=\"leaked-memo\"> with <p>",
                'style': ".leaked-memo -> typewriter font, stamped, official",
            },
            {
                'name': 'pattern_claim',
                'content': "PATTERN: [a claim that 'the pattern is obvious']",
                'html': "PATTERN -> <p class=\"pattern-claim\">",
                'style': ".pattern-claim -> bold, centered, dramatic",
            },
            {
                'name': 'debunked_note',
                'content': "DEBUNKED: [a note claiming the conspiracy was 'debunked' (it wasn't)]",
                'html': "DEBUNKED -> <p class=\"debunked-note\">",
                'style': ".debunked-note -> strikethrough, muted, crossed-out feel",
            },
            {
                'name': 'map_marker',
                'content': "MAP: [a 'map' description with marked locations]",
                'html': "MAP -> <div class=\"map-marker\"> with <p>",
                'style': ".map-marker -> bordered, pin icons, map feel",
            },
            {
                'name': 'code_break',
                'content': "CODE: [a 'decoded' message]",
                'html': "CODE -> <p class=\"code-break\">",
                'style': ".code-break -> monospace, highlighted, secret feel",
            },
            {
                'name': 'surveillance_log',
                'content': "SURVEILLANCE: [a surveillance log entry]",
                'html': "SURVEILLANCE -> <div class=\"surveillance-log\"> with <p>",
                'style': ".surveillance-log -> monospace, timestamp, clinical",
            },
            {
                'name': 'whistleblower',
                'content': "WHISTLEBLOWER: [a whistleblower's warning]",
                'html': "WHISTLEBLOWER -> <blockquote class=\"whistleblower\"> with <cite>",
                'style': ".whistleblower -> bold, red accent, urgent",
            },
            {
                'name': 'corkboard_title',
                'content': "BOARDTITLE: [a case-file title for the board]",
                'html': "BOARDTITLE -> <h2 class=\"corkboard-title\">",
                'style': ".corkboard-title -> marker-style, bold, centered",
            },
        ],
    },
    'cookbook': {
        'name': 'cookbook recipe',
        'content_styles': [
            (
                "Write like a cookbook recipe page. A recipe title, a story intro, an "
                "ingredients list, numbered steps, and a chef's note. Voice is warm, "
                "enthusiastic, and treats the topic as a dish to be prepared."
            ),
            (
                "Write like a food blog recipe. A long story intro about the topic, an "
                "ingredients list, numbered steps, a 'pro tip' box, and a 'did you make "
                "this?' closer. Voice is chatty and over-sharing."
            ),
            (
                "Write like a 1950s cookbook. A prim recipe title, a 'housewife' intro, "
                "an ingredients list, numbered steps, and a 'serving suggestion'. Voice "
                "is cheerful and dated."
            ),
        ],
        'layouts': [
            (
                "Build a recipe page: a header with the dish name, a hero image slot, an "
                "ingredients list, numbered preparation steps, and a chef's note box at the "
                "bottom. One flowing recipe card."
            ),
            (
                "Build a recipe card: a title header, a story intro, an ingredients "
                "list, numbered steps, a pro tip box, and a footer note. One continuous "
                "card."
            ),
            (
                "Build a cookbook page: a recipe title, a serving suggestion image, "
                "an ingredients list, numbered steps, and a 'chef's secret' box. "
                "One flowing page."
            ),
        ],
        'themes': [
            (
                "Cookbook look: cream paper background, warm red and green accents, serif "
                "headings, a dashed-border ingredients box, and a handwritten-feel chef's note. "
                "Unified and appetizing."
            ),
            (
                "Food blog look: white background, bright orange accents, clean sans-serif, "
                "a bordered ingredients box, and a 'pro tip' highlight. Unified and modern."
            ),
            (
                "Retro cookbook look: pastel background, teal and pink accents, a "
                "dashed ingredients box, and a vintage serif. Unified and kitschy."
            ),
        ],
        'image_ranges': [(2, 3), (3, 4), (1, 3)],
        'elements': [
            {
                'name': 'ingredients',
                'content': "INGREDIENTS: [title]\n- [ingredient]\n- [ingredient]\n- [ingredient]",
                'html': "INGREDIENTS -> <div class=\"ingredients\"> with <h3> and <ul>",
                'style': ".ingredients -> dashed-border box, checklist feel",
            },
            {
                'name': 'steps',
                'content': "STEPS: [title]\n1. [step]\n2. [step]\n3. [step]",
                'html': "STEPS -> <div class=\"recipe-steps\"> with <h3> and <ol>",
                'style': ".recipe-steps -> numbered, bold step numbers",
            },
            {
                'name': 'chefs_note',
                'content': "CHEFSNOTE: [a handwritten-feel chef's note]",
                'html': "CHEFSNOTE -> <div class=\"chefs-note\"> with <p>",
                'style': ".chefs-note -> handwritten font, dashed border, warm accent",
            },
            {
                'name': 'serving_suggestion',
                'content': "SERVING: [a 'serving suggestion' line]",
                'html': "SERVING -> <p class=\"serving-suggestion\">",
                'style': ".serving-suggestion -> small italic text, muted",
            },
            {
                'name': 'prep_time',
                'content': "PREPTIME: [a fake prep and cook time]",
                'html': "PREPTIME -> <p class=\"prep-time\">",
                'style': ".prep-time -> small text, clock icon, muted",
            },
            {
                'name': 'story_intro',
                'content': "STORY: [a long story intro about the topic]",
                'html': "STORY -> <p class=\"story-intro\">",
                'style': ".story-intro -> italic, warm, personal",
            },
            {
                'name': 'pro_tip',
                'content': "PROTIP: [a cooking pro tip]",
                'html': "PROTIP -> <div class=\"cookbook-tip\"> with <p>",
                'style': ".cookbook-tip -> green box, lightbulb, bordered",
            },
            {
                'name': 'nutrition_facts',
                'content': "NUTRITION: [a fake nutrition facts table]",
                'html': "NUTRITION -> <table class=\"nutrition-facts\"> with <tbody>",
                'style': ".nutrition-facts -> small table, bordered, label feel",
            },
            {
                'name': 'substitutions',
                'content': "SUBSTITUTE: [title]\n- [ingredient]: [substitute]\n- [ingredient]: [substitute]",
                'html': "SUBSTITUTE -> <div class=\"substitutions\"> with <h3> and <ul>",
                'style': ".substitutions -> two-column, small text, bordered",
            },
            {
                'name': 'wine_pairing',
                'content': "PAIRING: [a 'pairs well with' line]",
                'html': "PAIRING -> <p class=\"wine-pairing\">",
                'style': ".wine-pairing -> italic, centered, elegant",
            },
            {
                'name': 'leftover_idea',
                'content': "LEFTOVER: [a 'what to do with leftovers' idea]",
                'html': "LEFTOVER -> <p class=\"leftover-idea\">",
                'style': ".leftover-idea -> small text, playful, muted",
            },
            {
                'name': 'recipe_rating',
                'content': "RATING: [a star rating for the recipe]",
                'html': "RATING -> <p class=\"recipe-rating\">",
                'style': ".recipe-rating -> star icons, bold, centered",
            },
            {
                'name': 'kitchen_tools',
                'content': "TOOLS: [title]\n- [tool]\n- [tool]",
                'html': "TOOLS -> <div class=\"kitchen-tools\"> with <h3> and <ul>",
                'style': ".kitchen-tools -> small text, bordered, checklist feel",
            },
            {
                'name': 'did_you_make',
                'content': "DIDYOUMAKE: [a 'did you make this?' closer]",
                'html': "DIDYOUMAKE -> <p class=\"did-you-make\">",
                'style': ".did-you-make -> italic, centered, friendly",
            },
        ],
    },
    'scientific_paper': {
        'name': 'scientific paper',
        'content_styles': [
            (
                "Write like a scientific paper about the topic. Abstract, methods, results, "
                "discussion, and footnotes. Voice is dry, formal, and absurdly rigorous about "
                "nonsense. Cite fake sources with fake author names."
            ),
            (
                "Write like a peer-reviewed paper that somehow got published. Abstract, "
                "methods, results with a table, discussion, and a 'conflict of interest' "
                "note. Voice is formal and increasingly desperate to justify nonsense."
            ),
            (
                "Write like a grant proposal for absurd research. Abstract, background, "
                "proposed methods, expected results, and a budget. Voice is academic and "
                "overly confident."
            ),
        ],
        'layouts': [
            (
                "Build a paper: a title header with authors, an abstract box, numbered sections "
                "(Introduction, Methods, Results, Discussion), a table for results, and a "
                "footnote/references section. One continuous academic document."
            ),
            (
                "Build a paper: a title header, an abstract, numbered sections, a results "
                "table, a discussion, and a references list. Single column, continuous."
            ),
            (
                "Build a grant proposal: a title header, an abstract, background "
                "sections, a methods section, a budget table, and a references list. "
                "One continuous document."
            ),
        ],
        'themes': [
            (
                "Academic look: white background, black serif text, blue section headings, "
                "double-spaced feel, and a subtle gray abstract box. Unified and scholarly."
            ),
            (
                "Journal look: white background, black text, a single accent color for "
                "headings, a bordered abstract box, and a serif font. Unified and formal."
            ),
            (
                "Preprint look: white background, monospace accents, a gray abstract "
                "box, and a clean sans-serif. Unified and modern."
            ),
        ],
        'image_ranges': [(1, 2), (0, 2), (1, 3)],
        'elements': [
            {
                'name': 'abstract',
                'content': "ABSTRACT: [a formal abstract of the 'research']",
                'html': "ABSTRACT -> <div class=\"abstract\"> with <h3> and <p>",
                'style': ".abstract -> gray box, bordered, small text",
            },
            {
                'name': 'methods',
                'content': "METHODS: [a description of the absurd 'methodology']",
                'html': "METHODS -> <section class=\"methods\"> with <h2> and <p>",
                'style': ".methods -> standard section, serif heading",
            },
            {
                'name': 'results_table',
                'content': "RESULTS: [title]\n- [metric]: [fake value]\n- [metric]: [fake value]",
                'html': "RESULTS -> <table class=\"results-table\"> with <thead>/<tbody>",
                'style': ".results-table -> striped rows, bold header, bordered",
            },
            {
                'name': 'footnote',
                'content': "FOOTNOTE: [a numbered footnote with a fake source]",
                'html': "FOOTNOTE -> <p class=\"footnote\">",
                'style': ".footnote -> small text, superscript number, muted",
            },
            {
                'name': 'citation',
                'content': "CITATION: [a fake academic citation]",
                'html': "CITATION -> <p class=\"citation\">",
                'style': ".citation -> small text, hanging indent, muted",
            },
            {
                'name': 'discussion',
                'content': "DISCUSSION: [a discussion section defending the nonsense]",
                'html': "DISCUSSION -> <section class=\"discussion\"> with <h2> and <p>",
                'style': ".discussion -> standard section, serif heading",
            },
            {
                'name': 'conflict_of_interest',
                'content': "CONFLICT: [a 'conflict of interest' disclosure]",
                'html': "CONFLICT -> <p class=\"conflict-of-interest\">",
                'style': ".conflict-of-interest -> small text, muted, formal",
            },
            {
                'name': 'acknowledgments',
                'content': "ACKNOWLEDGMENTS: [a thank-you note to absurd people]",
                'html': "ACKNOWLEDGMENTS -> <p class=\"acknowledgments\">",
                'style': ".acknowledgments -> small italic text, muted",
            },
            {
                'name': 'hypothesis',
                'content': "HYPOTHESIS: [a formal statement of the absurd hypothesis]",
                'html': "HYPOTHESIS -> <p class=\"hypothesis\">",
                'style': ".hypothesis -> italic, centered, formal",
            },
            {
                'name': 'peer_review',
                'content': "PEERREVIEW: [a 'peer review' comment on the paper]",
                'html': "PEERREVIEW -> <blockquote class=\"peer-review\"> with <cite>",
                'style': ".peer-review -> italic, bordered, critical feel",
            },
            {
                'name': 'appendix',
                'content': "APPENDIX: [an appendix with absurd supplementary data]",
                'html': "APPENDIX -> <section class=\"appendix\"> with <h2> and <p>",
                'style': ".appendix -> smaller text, muted, technical",
            },
            {
                'name': 'keywords',
                'content': "KEYWORDS: [title]\n- [keyword]\n- [keyword]",
                'html': "KEYWORDS -> <p class=\"keywords\"> with <ul>",
                'style': ".keywords -> small text, comma-separated, muted",
            },
            {
                'name': 'funding_note',
                'content': "FUNDING: [a fake funding source]",
                'html': "FUNDING -> <p class=\"funding-note\">",
                'style': ".funding-note -> small text, muted, formal",
            },
            {
                'name': 'limitations',
                'content': "LIMITATIONS: [a 'limitations' section admitting the nonsense]",
                'html': "LIMITATIONS -> <section class=\"limitations\"> with <h2> and <p>",
                'style': ".limitations -> standard section, apologetic tone",
            },
            {
                'name': 'data_availability',
                'content': "DATA: [a 'data availability' statement]",
                'html': "DATA -> <p class=\"data-availability\">",
                'style': ".data-availability -> small text, muted, formal",
            },
        ],
    },
    'yearbook': {
        'name': 'yearbook page',
        'content_styles': [
            (
                "Write like a high school yearbook. Superlatives ('Most Likely To...'), "
                "portrait captions, student quotes, and a class photo section. Voice is "
                "cheesy, nostalgic, and earnest about the topic."
            ),
            (
                "Write like a college yearbook. 'Senior quotes', club photos, superlatives, "
                "and a 'where are they now' section. Voice is nostalgic and slightly "
                "self-aware about the absurdity."
            ),
            (
                "Write like a middle school yearbook. Handwritten-feel messages, "
                "'best friends forever' energy, superlatives, and a class photo section. "
                "Voice is earnest and adorable."
            ),
        ],
        'layouts': [
            (
                "Build a yearbook spread: a header with the year, a grid of 'portrait' image "
                "slots with captions, a superlatives list, and a quotes section. Two-column "
                "layout like a real yearbook page."
            ),
            (
                "Build a yearbook page: a 'class of' header, a grid of portrait image "
                "slots, a superlatives list, and a senior quotes section. One continuous "
                "spread."
            ),
            (
                "Build a yearbook section: a header, a photo grid, superlatives, "
                "quotes, and a 'memories' note. Flows as one nostalgic page."
            ),
        ],
        'themes': [
            (
                "Yearbook look: school colors (navy and gold), white background, bold sans-serif "
                "headings, portrait frames with borders, and a 'class of' banner. Unified and "
                "nostalgic."
            ),
            (
                "College yearbook look: dark green and gold, white background, portrait "
                "frames, and a clean serif. Unified and collegiate."
            ),
            (
                "Retro yearbook look: muted browns and oranges, white background, "
                "portrait frames, and a 70s font. Unified and vintage."
            ),
        ],
        'image_ranges': [(4, 6), (5, 7), (3, 5)],
        'elements': [
            {
                'name': 'superlatives',
                'content': "SUPERLATIVES: [title]\n- [category]: [winner]\n- [category]: [winner]",
                'html': "SUPERLATIVES -> <div class=\"superlatives\"> with <h3> and <ul>",
                'style': ".superlatives -> gold award-list, ribbon accents, bold categories",
            },
            {
                'name': 'senior_quote',
                'content': "SENIORQUOTE: [a 'senior quote' from the topic]",
                'html': "SENIORQUOTE -> <blockquote class=\"senior-quote\"> with <cite>",
                'style': ".senior-quote -> italic, centered, decorative quote marks",
            },
            {
                'name': 'portrait_caption',
                'content': "PORTRAIT: [a caption for a 'portrait' image]",
                'html': "PORTRAIT -> <figcaption class=\"portrait-caption\">",
                'style': ".portrait-caption -> small text, bordered, name-tag feel",
            },
            {
                'name': 'club_photo',
                'content': "CLUB: [a 'club photo' description with members]",
                'html': "CLUB -> <figure class=\"club-photo\"> with <img> and <figcaption>",
                'style': ".club-photo -> bordered frame, group-photo feel",
            },
            {
                'name': 'class_of',
                'content': "CLASSOF: [a 'class of' banner line]",
                'html': "CLASSOF -> <h2 class=\"class-of\">",
                'style': ".class-of -> bold, centered, school colors",
            },
            {
                'name': 'memories',
                'content': "MEMORIES: [a 'favorite memories' section]",
                'html': "MEMORIES -> <section class=\"memories\"> with <h2> and <p>",
                'style': ".memories -> warm background, nostalgic feel",
            },
            {
                'name': 'handwritten_note',
                'content': "HANDWRITTEN: [a handwritten-feel message to the topic]",
                'html': "HANDWRITTEN -> <p class=\"handwritten-note\">",
                'style': ".handwritten-note -> handwriting font, warm accent",
            },
            {
                'name': 'where_are_they',
                'content': "WHEREARE: [a 'where are they now' section]",
                'html': "WHEREARE -> <div class=\"where-are-they\"> with <h3> and <ul>",
                'style': ".where-are-they -> small text, bordered, nostalgic",
            },
            {
                'name': 'faculty_shoutout',
                'content': "FACULTY: [a 'shoutout to faculty' line]",
                'html': "FACULTY -> <p class=\"faculty-shoutout\">",
                'style': ".faculty-shoutout -> small italic text, muted",
            },
            {
                'name': 'sports_section',
                'content': "SPORTS: [a 'sports' section about the topic]",
                'html': "SPORTS -> <section class=\"sports-section\"> with <h2> and <p>",
                'style': ".sports-section -> school colors, bold headings",
            },
            {
                'name': 'best_friends',
                'content': "BESTFRIENDS: [a 'best friends forever' dedication]",
                'html': "BESTFRIENDS -> <p class=\"best-friends\">",
                'style': ".best-friends -> handwritten font, hearts, warm",
            },
            {
                'name': 'yearbook_signature',
                'content': "SIGNATURE: [a 'signature' line from the topic]",
                'html': "SIGNATURE -> <p class=\"yearbook-signature\">",
                'style': ".yearbook-signature -> script font, centered, personal",
            },
            {
                'name': 'candid_photo',
                'content': "CANDID: [a 'candid photo' description]",
                'html': "CANDID -> <figure class=\"candid-photo\"> with <img> and <figcaption>",
                'style': ".candid-photo -> tilted frame, candid feel",
            },
            {
                'name': 'dedication_page',
                'content': "DEDICATION: [a 'this yearbook is dedicated to' line]",
                'html': "DEDICATION -> <p class=\"dedication-page\">",
                'style': ".dedication-page -> centered, formal, gold accent",
            },
        ],
    },
    'court_ruling': {
        'name': 'court ruling',
        'content_styles': [
            (
                "Write like a court ruling document. Case name, charges, evidence, verdict, "
                "and sentence. Voice is formal, legalistic, and deadpan about absurd charges "
                "related to the topic."
            ),
            (
                "Write like a supreme court opinion. A case name, a 'we hold that' "
                "framing, majority reasoning, a dissenting opinion, and a ruling. Voice "
                "is grand and legalistic."
            ),
            (
                "Write like a traffic court citation. A case number, the 'offense', "
                "the officer's account, the fine, and a 'you may appeal' note. Voice "
                "is bureaucratic and dry."
            ),
        ],
        'layouts': [
            (
                "Build a legal document: a case header, a charges list, an evidence section, "
                "a verdict box, and a sentence line. Single column, formal, with clear "
                "section headings."
            ),
            (
                "Build a ruling: a case header, a 'we hold that' section, majority "
                "reasoning, a dissenting opinion box, and a ruling line. Single column, "
                "formal."
            ),
            (
                "Build a citation: a case header, an offense list, an account section, "
                "a fine box, and an appeal note. Single column, bureaucratic."
            ),
        ],
        'themes': [
            (
                "Legal look: white paper, black serif text, a red seal accent, bold section "
                "headings, and thin rules between sections. Unified and official."
            ),
            (
                "Supreme court look: cream paper, black serif text, a gold seal accent, "
                "and formal section headings. Unified and grand."
            ),
            (
                "Bureaucratic look: white paper, black text, a red 'FINE' box, and a "
                "monospace case number. Unified and dry."
            ),
        ],
        'image_ranges': [(0, 1), (0, 2), (1, 2)],
        'elements': [
            {
                'name': 'charges',
                'content': "CHARGES: [title]\n- [charge]\n- [charge]\n- [charge]",
                'html': "CHARGES -> <div class=\"charges\"> with <h3> and <ul>",
                'style': ".charges -> numbered, bold, legal feel",
            },
            {
                'name': 'verdict',
                'content': "VERDICT: [the formal verdict]",
                'html': "VERDICT -> <div class=\"verdict\"> with <p>",
                'style': ".verdict -> bold, centered, red seal accent",
            },
            {
                'name': 'evidence',
                'content': "EVIDENCE: [a description of the absurd evidence]",
                'html': "EVIDENCE -> <section class=\"evidence\"> with <h2> and <p>",
                'style': ".evidence -> standard section, formal heading",
            },
            {
                'name': 'case_number',
                'content': "CASENUM: [a fake case number]",
                'html': "CASENUM -> <p class=\"case-number\">",
                'style': ".case-number -> monospace, small, muted",
            },
            {
                'name': 'sentence',
                'content': "SENTENCE: [the absurd sentence handed down]",
                'html': "SENTENCE -> <p class=\"sentence\">",
                'style': ".sentence -> bold, centered, formal",
            },
            {
                'name': 'dissenting_opinion',
                'content': "DISSENT: [a dissenting opinion from a 'judge']",
                'html': "DISSENT -> <blockquote class=\"dissenting-opinion\"> with <cite>",
                'style': ".dissenting-opinion -> italic, bordered, contrasting",
            },
            {
                'name': 'we_hold',
                'content': "WEHOLD: [a 'we hold that' statement]",
                'html': "WEHOLD -> <p class=\"we-hold\">",
                'style': ".we-hold -> bold, centered, formal",
            },
            {
                'name': 'court_seal',
                'content': "SEAL: [a description of the 'court seal']",
                'html': "SEAL -> <p class=\"court-seal\">",
                'style': ".court-seal -> centered, gold, formal",
            },
            {
                'name': 'appeal_note',
                'content': "APPEAL: [a 'you may appeal' note]",
                'html': "APPEAL -> <p class=\"appeal-note\">",
                'style': ".appeal-note -> small text, muted, formal",
            },
            {
                'name': 'officer_account',
                'content': "OFFICER: [the 'officer's account' of the offense]",
                'html': "OFFICER -> <blockquote class=\"officer-account\"> with <cite>",
                'style': ".officer-account -> italic, bordered, official",
            },
            {
                'name': 'fine_box',
                'content': "FINE: [the absurd fine amount]",
                'html': "FINE -> <div class=\"fine-box\"> with <p>",
                'style': ".fine-box -> bold, red border, urgent",
            },
            {
                'name': 'legal_jargon',
                'content': "JARGON: [a paragraph of dense legal jargon about the topic]",
                'html': "JARGON -> <p class=\"legal-jargon\">",
                'style': ".legal-jargon -> small text, dense, formal",
            },
            {
                'name': 'court_date',
                'content': "COURTDATE: [a fake court date]",
                'html': "COURTDATE -> <p class=\"court-date\">",
                'style': ".court-date -> small text, muted, formal",
            },
            {
                'name': 'bail_ruling',
                'content': "BAIL: [a 'bail is set at' line]",
                'html': "BAIL -> <p class=\"bail-ruling\">",
                'style': ".bail-ruling -> bold, centered, formal",
            },
        ],
    },
    'obituary': {
        'name': 'obituary',
        'content_styles': [
            (
                "Write like an obituary for the topic. Born/died dates, a life summary, "
                "'survived by' list, and a memorial note. Voice is solemn, respectful, and "
                "quietly funny about the absurdity."
            ),
            (
                "Write like a celebrity obituary. A life in highlights, 'the world "
                "mourns' framing, quotes from 'friends', and a legacy note. Voice is "
                "grand and slightly overblown."
            ),
            (
                "Write like a small-town newspaper obituary. A humble life summary, "
                "'beloved by' list, a funeral note, and a 'in lieu of flowers' line. "
                "Voice is warm and plain."
            ),
        ],
        'layouts': [
            (
                "Build an obituary: a header with the name and dates, a portrait image slot, "
                "a life summary, a 'survived by' list, and a memorial footer. Single column, "
                "centered, bordered like a newspaper obituary."
            ),
            (
                "Build an obituary: a header, a portrait image slot, a life summary, "
                "a 'survived by' list, and a memorial note. Single column, bordered."
            ),
            (
                "Build a memorial: a header, a photo slot, a life summary, a 'beloved "
                "by' list, and a funeral note. Single column, centered."
            ),
        ],
        'themes': [
            (
                "Obituary look: white background, black serif text, a thin black border frame, "
                "a small portrait frame, and muted gray accents. Unified and somber."
            ),
            (
                "Newspaper obituary look: off-white background, black serif text, a "
                "double border, and a small portrait frame. Unified and classic."
            ),
            (
                "Memorial look: soft gray background, dark text, a bordered photo frame, "
                "and a serif font. Unified and gentle."
            ),
        ],
        'image_ranges': [(1, 2), (0, 2), (1, 3)],
        'elements': [
            {
                'name': 'life_summary',
                'content': "LIFE: [a life summary of the topic]",
                'html': "LIFE -> <p class=\"life-summary\">",
                'style': ".life-summary -> serif, centered, somber",
            },
            {
                'name': 'survived_by',
                'content': "SURVIVED: [title]\n- [survivor]\n- [survivor]",
                'html': "SURVIVED -> <div class=\"survived-by\"> with <h3> and <ul>",
                'style': ".survived-by -> small text, bordered, muted",
            },
            {
                'name': 'memorial_note',
                'content': "MEMORIAL: [a memorial note about the topic]",
                'html': "MEMORIAL -> <p class=\"memorial-note\">",
                'style': ".memorial-note -> italic, centered, somber",
            },
            {
                'name': 'born_died',
                'content': "DATES: [born date] - [died date]",
                'html': "DATES -> <p class=\"born-died\">",
                'style': ".born-died -> centered, serif, muted",
            },
            {
                'name': 'in_lieu',
                'content': "INLIEU: [an 'in lieu of flowers' line]",
                'html': "INLIEU -> <p class=\"in-lieu\">",
                'style': ".in-lieu -> small italic text, muted",
            },
            {
                'name': 'funeral_arrangements',
                'content': "FUNERAL: [funeral arrangement details]",
                'html': "FUNERAL -> <p class=\"funeral-arrangements\">",
                'style': ".funeral-arrangements -> small text, muted, formal",
            },
            {
                'name': 'legacy',
                'content': "LEGACY: [a 'legacy' paragraph about the topic]",
                'html': "LEGACY -> <p class=\"legacy\">",
                'style': ".legacy -> serif, centered, warm",
            },
            {
                'name': 'world_mourns',
                'content': "MOURNS: [a 'the world mourns' framing]",
                'html': "MOURNS -> <p class=\"world-mourns\">",
                'style': ".world-mourns -> bold, centered, dramatic",
            },
            {
                'name': 'friend_quote',
                'content': "FRIEND: [a quote from a 'friend' of the topic]",
                'html': "FRIEND -> <blockquote class=\"friend-quote\"> with <cite>",
                'style': ".friend-quote -> italic, bordered, somber",
            },
            {
                'name': 'obituary_border',
                'content': "OBITBORDER: [a decorative obituary border line]",
                'html': "OBITBORDER -> <hr class=\"obituary-border\">",
                'style': ".obituary-border -> thin black rule, centered",
            },
            {
                'name': 'guestbook',
                'content': "GUESTBOOK: [a 'sign the guestbook' note]",
                'html': "GUESTBOOK -> <p class=\"guestbook\">",
                'style': ".guestbook -> small text, muted, formal",
            },
            {
                'name': 'charity_note',
                'content': "CHARITY: [a 'donations to' line]",
                'html': "CHARITY -> <p class=\"charity-note\">",
                'style': ".charity-note -> small text, muted, formal",
            },
        ],
    },
    'product_recall': {
        'name': 'product recall notice',
        'content_styles': [
            (
                "Write like an official product recall notice. The affected 'product' (the "
                "topic), the reason for recall, affected units, and required action. Voice is "
                "bureaucratic, urgent, and absurdly serious."
            ),
            (
                "Write like a food safety recall. The affected 'product', the reason, "
                "lot numbers, symptoms to watch for, and a refund line. Voice is "
                "clinical and urgent."
            ),
            (
                "Write like a toy recall notice. The affected 'product', the hazard, "
                "the number of units, and a 'what to do' section. Voice is concerned "
                "and bureaucratic."
            ),
        ],
        'layouts': [
            (
                "Build a recall notice: a red header banner, a product description, a list of "
                "affected units, a reason section, and an 'action required' box. Single column, "
                "official document layout."
            ),
            (
                "Build a recall: a red banner, a product description, a lot numbers "
                "list, a hazard section, and a 'what to do' box. Single column, official."
            ),
            (
                "Build a notice: a header, a product description, an affected units "
                "table, a reason section, and an action box. Single column, official."
            ),
        ],
        'themes': [
            (
                "Recall look: white background, red header banner, black text, bold warning "
                "boxes with red borders, and a government-document feel. Unified and urgent."
            ),
            (
                "FDA look: white background, a blue header, black text, bordered "
                "warning boxes, and a government feel. Unified and official."
            ),
            (
                "Urgent notice look: white background, a red banner, black text, "
                "yellow warning boxes, and a bold sans-serif. Unified and alarming."
            ),
        ],
        'image_ranges': [(1, 2), (0, 2), (1, 3)],
        'elements': [
            {
                'name': 'affected_units',
                'content': "UNITS: [title]\n- [unit]\n- [unit]\n- [unit]",
                'html': "UNITS -> <div class=\"affected-units\"> with <h3> and <ul>",
                'style': ".affected-units -> bordered list, bold, official",
            },
            {
                'name': 'reason_for_recall',
                'content': "REASON: [the absurd reason for the recall]",
                'html': "REASON -> <section class=\"reason-for-recall\"> with <h2> and <p>",
                'style': ".reason-for-recall -> standard section, urgent heading",
            },
            {
                'name': 'action_required',
                'content': "ACTION: [the 'action required' instructions]",
                'html': "ACTION -> <div class=\"action-required\"> with <p>",
                'style': ".action-required -> bold box, red border, urgent",
            },
            {
                'name': 'lot_numbers',
                'content': "LOTS: [title]\n- [lot number]\n- [lot number]",
                'html': "LOTS -> <div class=\"lot-numbers\"> with <h3> and <ul>",
                'style': ".lot-numbers -> monospace, bordered, small text",
            },
            {
                'name': 'symptoms',
                'content': "SYMPTOMS: [title]\n- [symptom]\n- [symptom]",
                'html': "SYMPTOMS -> <div class=\"symptoms\"> with <h3> and <ul>",
                'style': ".symptoms -> bordered list, warning accents",
            },
            {
                'name': 'refund_line',
                'content': "REFUND: [a 'full refund' line]",
                'html': "REFUND -> <p class=\"refund-line\">",
                'style': ".refund-line -> bold, centered, official",
            },
            {
                'name': 'hazard_warning',
                'content': "HAZARD: [a description of the 'hazard']",
                'html': "HAZARD -> <div class=\"hazard-warning\"> with <p>",
                'style': ".hazard-warning -> yellow box, bold border, warning icon",
            },
            {
                'name': 'recall_number',
                'content': "RECALLNUM: [a fake recall number]",
                'html': "RECALLNUM -> <p class=\"recall-number\">",
                'style': ".recall-number -> monospace, small, muted",
            },
            {
                'name': 'distribution',
                'content': "DISTRIBUTION: [a 'distributed in' line]",
                'html': "DISTRIBUTION -> <p class=\"distribution\">",
                'style': ".distribution -> small text, muted, official",
            },
            {
                'name': 'contact_hotline',
                'content': "HOTLINE: [a 'call this hotline' line]",
                'html': "HOTLINE -> <p class=\"contact-hotline\">",
                'style': ".contact-hotline -> bold, centered, urgent",
            },
            {
                'name': 'regulator_statement',
                'content': "REGULATOR: [a statement from the 'regulator']",
                'html': "REGULATOR -> <blockquote class=\"regulator-statement\"> with <cite>",
                'style': ".regulator-statement -> italic, bordered, official",
            },
            {
                'name': 'affected_dates',
                'content': "DATES: [a 'sold between' date range]",
                'html': "DATES -> <p class=\"affected-dates\">",
                'style': ".affected-dates -> small text, muted, official",
            },
            {
                'name': 'safety_instructions',
                'content': "SAFETY: [safety instructions for the 'product']",
                'html': "SAFETY -> <div class=\"safety-instructions\"> with <p>",
                'style': ".safety-instructions -> bordered, numbered, official",
            },
            {
                'name': 'apology',
                'content': "APOLOGY: [a corporate apology for the recall]",
                'html': "APOLOGY -> <p class=\"apology\">",
                'style': ".apology -> italic, centered, contrite",
            },
        ],
    },
    'infomercial': {
        'name': 'infomercial',
        'content_styles': [
            (
                "Write like a late-night infomercial. Problem, solution, 'but wait there's "
                "more!', testimonials, and a CALL NOW closer. Voice is hype-man energy, "
                "shouty, and desperate to sell the topic."
            ),
            (
                "Write like a home shopping network pitch. A 'viewers at home' framing, "
                "a product demo, a 'call now' offer, and a 'operators standing by' "
                "closer. Voice is polished and relentless."
            ),
            (
                "Write like a crowdfunding campaign pitch. A problem, a solution, "
                "stretch goals, backer testimonials, and a 'pledge now' closer. Voice "
                "is excited and slightly desperate."
            ),
        ],
        'layouts': [
            (
                "Build an infomercial page: a big product header, a problem section, a "
                "solution section, a 'but wait' callout, testimonial boxes, and a giant "
                "CALL NOW footer. Bold, loud, single flowing pitch."
            ),
            (
                "Build a pitch page: a product header, a problem section, a demo "
                "section, a 'limited offer' box, testimonials, and a CALL NOW footer. "
                "One loud pitch."
            ),
            (
                "Build a campaign page: a header, a problem section, a solution, "
                "stretch goal boxes, testimonials, and a 'pledge now' footer. One "
                "flowing pitch."
            ),
        ],
        'themes': [
            (
                "Infomercial look: bright yellow and red, black bold text, flashing-energy "
                "accents, big price tags, and a 'limited time' banner. One loud unified palette."
            ),
            (
                "HSN look: bright blue and white, bold text, a 'call now' banner, "
                "and a clean sans-serif. Unified and polished."
            ),
            (
                "Crowdfunding look: white background, a single bold accent color, "
                "progress-bar boxes, and a modern sans-serif. Unified and energetic."
            ),
        ],
        'image_ranges': [(2, 3), (1, 3), (2, 4)],
        'elements': [
            {
                'name': 'call_now',
                'content': "CALLNOW: [a 'CALL NOW' closer with a fake number]",
                'html': "CALLNOW -> <div class=\"call-now\"> with <p>",
                'style': ".call-now -> huge bold text, red/yellow, flashing feel",
            },
            {
                'name': 'but_wait',
                'content': "BUTWAIT: [a 'but wait, there's more!' offer]",
                'html': "BUTWAIT -> <div class=\"but-wait\"> with <p>",
                'style': ".but-wait -> bold callout, bright border, excited",
            },
            {
                'name': 'testimonial',
                'content': "TESTIMONIAL: [a fake customer testimonial]\nSOURCE: [fake customer]",
                'html': "TESTIMONIAL -> <blockquote class=\"infomercial-testimonial\"> with <cite>",
                'style': ".infomercial-testimonial -> italic, bordered, star accents",
            },
            {
                'name': 'problem_solution',
                'content': "PROBLEM: [the 'problem' the topic solves]\nSOLUTION: [the 'solution']",
                'html': "PROBLEM -> <div class=\"problem-solution\"> with two <p> blocks",
                'style': ".problem-solution -> two-column, contrasting colors",
            },
            {
                'name': 'limited_time',
                'content': "LIMITED: [a 'limited time offer' banner]",
                'html': "LIMITED -> <div class=\"limited-time\"> with <p>",
                'style': ".limited-time -> red banner, all-caps, urgent",
            },
            {
                'name': 'price_tag',
                'content': "PRICE: [a dramatic price with a 'was' price]",
                'html': "PRICE -> <p class=\"infomercial-price\">",
                'style': ".infomercial-price -> huge bold price, strikethrough was-price",
            },
            {
                'name': 'bonus_offer',
                'content': "BONUS: [a 'free bonus' offer]",
                'html': "BONUS -> <div class=\"bonus-offer\"> with <p>",
                'style': ".bonus-offer -> green box, bold, exciting",
            },
            {
                'name': 'operators_standing',
                'content': "OPERATORS: [a 'operators are standing by' line]",
                'html': "OPERATORS -> <p class=\"operators-standing\">",
                'style': ".operators-standing -> small text, centered, urgent",
            },
            {
                'name': 'stretch_goal',
                'content': "STRETCH: [a 'stretch goal' for the campaign]",
                'html': "STRETCH -> <div class=\"stretch-goal\"> with <p>",
                'style': ".stretch-goal -> progress-bar feel, bold",
            },
            {
                'name': 'demo_section',
                'content': "DEMO: [a 'product demo' description]",
                'html': "DEMO -> <section class=\"demo-section\"> with <h2> and <p>",
                'style': ".demo-section -> bold heading, dramatic text",
            },
            {
                'name': 'guarantee',
                'content': "GUARANTEE: [a 'money-back guarantee' line]",
                'html': "GUARANTEE -> <p class=\"guarantee\">",
                'style': ".guarantee -> bold, centered, official",
            },
            {
                'name': 'as_seen_on',
                'content': "ASSEEN: [an 'as seen on TV' line]",
                'html': "ASSEEN -> <p class=\"as-seen-on\">",
                'style': ".as-seen-on -> small caps, centered, muted",
            },
            {
                'name': 'hurry',
                'content': "HURRY: [a 'hurry, supplies are limited' line]",
                'html': "HURRY -> <p class=\"hurry\">",
                'style': ".hurry -> bold, red, urgent",
            },
            {
                'name': 'fine_print',
                'content': "FINEPRINT: [absurd fine print at the bottom]",
                'html': "FINEPRINT -> <p class=\"fine-print\">",
                'style': ".fine-print -> tiny text, muted, legal feel",
            },
        ],
    },
    'choose_your_adventure': {
        'name': 'choose-your-own-adventure',
        'content_styles': [
            (
                "Write like a choose-your-own-adventure book. Second person, branching "
                "options, 'if you choose A, go to page X'. Voice is dramatic and immersive, "
                "treating the topic as an adventure."
            ),
            (
                "Write like a text adventure game. Second person, a room description, "
                "commands, and 'you see' framing. Voice is terse and atmospheric."
            ),
            (
                "Write like a 'which path will you take' quiz. A scenario, options, "
                "and outcomes. Voice is playful and dramatic."
            ),
        ],
        'layouts': [
            (
                "Build an adventure page: a title header, a story paragraph, then option cards "
                "with choices, each leading to another section. Sections flow down the page "
                "as one branching narrative."
            ),
            (
                "Build a text adventure: a title header, a room description, a list "
                "of commands, and a 'you are here' marker. Sections flow as one "
                "narrative."
            ),
            (
                "Build a path page: a title header, a scenario, option cards, and "
                "outcome sections. Flows as one branching story."
            ),
        ],
        'themes': [
            (
                "Adventure look: parchment background, dark brown text, option cards with "
                "borders, a compass or map accent, and a fantasy font. Unified and immersive."
            ),
            (
                "Text adventure look: black background, green monospace text, and a "
                "terminal feel. Unified and retro."
            ),
            (
                "Quiz look: white background, bold accent colors, option cards, and "
                "a playful sans-serif. Unified and fun."
            ),
        ],
        'image_ranges': [(1, 2), (0, 2), (1, 3)],
        'elements': [
            {
                'name': 'option_card',
                'content': "OPTION: [a choice]\n- [option A]\n- [option B]",
                'html': "OPTION -> <div class=\"option-card\"> with <h3> and <ul>",
                'style': ".option-card -> bordered card, hover feel, bold choices",
            },
            {
                'name': 'branching_path',
                'content': "BRANCH: [a 'if you chose X, go to Y' line]",
                'html': "BRANCH -> <p class=\"branching-path\">",
                'style': ".branching-path -> italic, centered, dramatic",
            },
            {
                'name': 'room_description',
                'content': "ROOM: [a second-person room description]",
                'html': "ROOM -> <p class=\"room-description\">",
                'style': ".room-description -> atmospheric, italic, immersive",
            },
            {
                'name': 'inventory',
                'content': "INVENTORY: [title]\n- [item]\n- [item]",
                'html': "INVENTORY -> <div class=\"inventory\"> with <h3> and <ul>",
                'style': ".inventory -> bordered box, item-list feel",
            },
            {
                'name': 'game_over',
                'content': "GAMEOVER: [a dramatic 'game over' ending]",
                'html': "GAMEOVER -> <p class=\"adventure-game-over\">",
                'style': ".adventure-game-over -> huge bold text, centered, dramatic",
            },
            {
                'name': 'you_win',
                'content': "YOUWIN: [a 'you win' ending]",
                'html': "YOUWIN -> <p class=\"you-win\">",
                'style': ".you-win -> bold, gold, celebratory",
            },
            {
                'name': 'secret_path',
                'content': "SECRET: [a hidden secret path]",
                'html': "SECRET -> <p class=\"secret-path\">",
                'style': ".secret-path -> hidden-feel, dashed border, mysterious",
            },
            {
                'name': 'encounter',
                'content': "ENCOUNTER: [a dramatic encounter description]",
                'html': "ENCOUNTER -> <p class=\"encounter\">",
                'style': ".encounter -> bold, atmospheric, dramatic",
            },
            {
                'name': 'map_section',
                'content': "MAP: [a description of the adventure map]",
                'html': "MAP -> <div class=\"adventure-map\"> with <p>",
                'style': ".adventure-map -> bordered, map feel, compass accent",
            },
            {
                'name': 'clue',
                'content': "CLUE: [a clue for the reader]",
                'html': "CLUE -> <p class=\"clue\">",
                'style': ".clue -> italic, muted, mysterious",
            },
            {
                'name': 'danger_warning',
                'content': "DANGER: [a 'danger ahead' warning]",
                'html': "DANGER -> <div class=\"danger-warning\"> with <p>",
                'style': ".danger-warning -> red box, bold border, urgent",
            },
            {
                'name': 'companion',
                'content': "COMPANION: [a companion character's line]",
                'html': "COMPANION -> <blockquote class=\"companion\"> with <cite>",
                'style': ".companion -> italic, bordered, character feel",
            },
            {
                'name': 'restart',
                'content': "RESTART: [a 'start over' line]",
                'html': "RESTART -> <p class=\"restart\">",
                'style': ".restart -> small text, centered, muted",
            },
            {
                'name': 'page_number',
                'content': "PAGENUM: [a fake 'turn to page X' line]",
                'html': "PAGENUM -> <p class=\"page-number\">",
                'style': ".page-number -> small text, centered, book feel",
            },
        ],
    },
    'horoscope_scroll': {
        'name': 'horoscope scroll',
        'content_styles': [
            (
                "Write like a horoscope column. Zodiac cards, lucky numbers, mystical "
                "predictions, and cosmic warnings. Voice is mystical, vague, and confidently "
                "nonsensical about the topic."
            ),
            (
                "Write like a fortune teller's reading. A 'the cards say' framing, "
                "predictions, lucky numbers, and a warning. Voice is mysterious and "
                "dramatic."
            ),
            (
                "Write like a cosmic newsletter. A 'this week in the stars' framing, "
                "zodiac predictions, a cosmic warning, and a 'blessed be' closer. "
                "Voice is spiritual and chatty."
            ),
        ],
        'layouts': [
            (
                "Build a horoscope page: a mystical header, a row of zodiac cards each with "
                "a sign, prediction, and lucky number, and a cosmic footer. Cards flow as one "
                "scroll."
            ),
            (
                "Build a reading: a mystical header, a 'the cards say' section, "
                "prediction cards, a lucky numbers list, and a warning box. One "
                "continuous scroll."
            ),
            (
                "Build a cosmic newsletter: a header, zodiac sections, a cosmic "
                "warning, and a 'blessed be' footer. One flowing scroll."
            ),
        ],
        'themes': [
            (
                "Mystical look: deep purple and indigo background, gold and star accents, "
                "serif headings, and a starry night feel. One unified cosmic palette."
            ),
            (
                "Tarot look: dark background, gold accents, card borders, and a "
                "mystical serif. Unified and mysterious."
            ),
            (
                "Cosmic look: navy background, silver and white accents, star "
                "patterns, and a clean sans-serif. Unified and celestial."
            ),
        ],
        'image_ranges': [(1, 2), (0, 2), (1, 3)],
        'elements': [
            {
                'name': 'zodiac_card',
                'content': "ZODIAC: [sign]\n[prediction for the sign]",
                'html': "ZODIAC -> <div class=\"zodiac-card\"> with <h3> and <p>",
                'style': ".zodiac-card -> bordered card, star accents, mystical",
            },
            {
                'name': 'lucky_numbers',
                'content': "LUCKY: [title]\n- [number]\n- [number]",
                'html': "LUCKY -> <div class=\"lucky-numbers\"> with <h3> and <ul>",
                'style': ".lucky-numbers -> gold numbers, bordered, mystical",
            },
            {
                'name': 'cosmic_warning',
                'content': "COSMICWARNING: [a vague cosmic warning]",
                'html': "COSMICWARNING -> <div class=\"cosmic-warning\"> with <p>",
                'style': ".cosmic-warning -> purple box, gold border, ominous",
            },
            {
                'name': 'prediction',
                'content': "PREDICTION: [a vague mystical prediction]",
                'html': "PREDICTION -> <p class=\"prediction\">",
                'style': ".prediction -> italic, centered, mystical",
            },
            {
                'name': 'the_cards_say',
                'content': "CARDS: [a 'the cards say' reading]",
                'html': "CARDS -> <p class=\"the-cards-say\">",
                'style': ".the-cards-say -> bold, centered, tarot feel",
            },
            {
                'name': 'blessed_be',
                'content': "BLESSED: [a 'blessed be' closer]",
                'html': "BLESSED -> <p class=\"blessed-be\">",
                'style': ".blessed-be -> italic, centered, spiritual",
            },
            {
                'name': 'moon_phase',
                'content': "MOON: [a moon phase reading]",
                'html': "MOON -> <p class=\"moon-phase\">",
                'style': ".moon-phase -> centered, celestial, muted",
            },
            {
                'name': 'compatibility',
                'content': "COMPATIBILITY: [a compatibility reading]",
                'html': "COMPATIBILITY -> <p class=\"compatibility\">",
                'style': ".compatibility -> centered, heart accent, mystical",
            },
            {
                'name': 'cosmic_advice',
                'content': "ADVICE: [vague cosmic advice]",
                'html': "ADVICE -> <p class=\"cosmic-advice\">",
                'style': ".cosmic-advice -> italic, centered, wise",
            },
            {
                'name': 'star_sign',
                'content': "STARSIGN: [a 'your star sign' line]",
                'html': "STARSIGN -> <p class=\"star-sign\">",
                'style': ".star-sign -> bold, centered, gold",
            },
            {
                'name': 'retrograde',
                'content': "RETROGRADE: [a 'mercury retrograde' warning]",
                'html': "RETROGRADE -> <p class=\"retrograde\">",
                'style': ".retrograde -> bold, red accent, urgent",
            },
            {
                'name': 'cosmic_newsletter',
                'content': "NEWSLETTER: [a 'this week in the stars' intro]",
                'html': "NEWSLETTER -> <p class=\"cosmic-newsletter\">",
                'style': ".cosmic-newsletter -> italic, centered, chatty",
            },
            {
                'name': 'tarot_spread',
                'content': "TAROT: [a tarot card reading]",
                'html': "TAROT -> <div class=\"tarot-spread\"> with <p>",
                'style': ".tarot-spread -> bordered, card feel, mystical",
            },
            {
                'name': 'cosmic_footer',
                'content': "COSMICFOOTER: [a cosmic sign-off line]",
                'html': "COSMICFOOTER -> <p class=\"cosmic-footer\">",
                'style': ".cosmic-footer -> small text, centered, muted",
            },
        ],
    },
    'resume': {
        'name': 'resume',
        'content_styles': [
            (
                "Write like a resume for the topic. Objective, experience, skills, and "
                "references. Voice is professional, buzzword-heavy, and absurdly qualified "
                "for nonsense."
            ),
            (
                "Write like a cover letter for the topic. A greeting, a 'why I'm "
                "perfect' section, experience highlights, and a sign-off. Voice is "
                "eager and overqualified."
            ),
            (
                "Write like a LinkedIn profile for the topic. A headline, an about "
                "section, experience, skills, and endorsements. Voice is professional "
                "and self-promoting."
            ),
        ],
        'layouts': [
            (
                "Build a resume: a header with name and contact, an objective section, an "
                "experience list, a skills list, and a references section. Single column, "
                "clean, professional document."
            ),
            (
                "Build a cover letter: a header, a greeting, a 'why me' section, "
                "experience highlights, and a sign-off. Single column, professional."
            ),
            (
                "Build a profile: a header, an about section, an experience list, "
                "a skills list, and endorsements. Single column, clean."
            ),
        ],
        'themes': [
            (
                "Resume look: white background, dark gray text, a single accent color for "
                "headings, clean sans-serif, and thin section rules. Unified and professional."
            ),
            (
                "Modern resume look: white background, a bold accent color, clean "
                "sans-serif, and a two-tone header. Unified and contemporary."
            ),
            (
                "Classic resume look: white background, black text, serif headings, "
                "and thin rules. Unified and traditional."
            ),
        ],
        'image_ranges': [(0, 1), (0, 2), (1, 2)],
        'elements': [
            {
                'name': 'objective',
                'content': "OBJECTIVE: [a buzzword-heavy objective statement]",
                'html': "OBJECTIVE -> <p class=\"objective\">",
                'style': ".objective -> italic, centered, professional",
            },
            {
                'name': 'experience',
                'content': "EXPERIENCE: [title]\n- [role]: [absurd achievement]\n- [role]: [absurd achievement]",
                'html': "EXPERIENCE -> <div class=\"experience\"> with <h3> and <ul>",
                'style': ".experience -> bordered, bold roles, professional",
            },
            {
                'name': 'skills',
                'content': "SKILLS: [title]\n- [skill]\n- [skill]",
                'html': "SKILLS -> <div class=\"skills\"> with <h3> and <ul>",
                'style': ".skills -> tag-style items, bordered, clean",
            },
            {
                'name': 'references',
                'content': "REFERENCES: [title]\n- [reference]\n- [reference]",
                'html': "REFERENCES -> <div class=\"references\"> with <h3> and <ul>",
                'style': ".references -> small text, muted, professional",
            },
            {
                'name': 'contact_info',
                'content': "CONTACT: [a fake contact line]",
                'html': "CONTACT -> <p class=\"contact-info\">",
                'style': ".contact-info -> small text, centered, muted",
            },
            {
                'name': 'education',
                'content': "EDUCATION: [a fake education entry]",
                'html': "EDUCATION -> <p class=\"education\">",
                'style': ".education -> small text, muted, professional",
            },
            {
                'name': 'achievements',
                'content': "ACHIEVEMENTS: [title]\n- [achievement]\n- [achievement]",
                'html': "ACHIEVEMENTS -> <div class=\"achievements\"> with <h3> and <ul>",
                'style': ".achievements -> bordered, bold, award feel",
            },
            {
                'name': 'summary',
                'content': "SUMMARY: [a professional summary paragraph]",
                'html': "SUMMARY -> <p class=\"summary\">",
                'style': ".summary -> italic, professional, clean",
            },
            {
                'name': 'certifications',
                'content': "CERTIFICATIONS: [title]\n- [certification]\n- [certification]",
                'html': "CERTIFICATIONS -> <div class=\"certifications\"> with <h3> and <ul>",
                'style': ".certifications -> small text, bordered, clean",
            },
            {
                'name': 'volunteer',
                'content': "VOLUNTEER: [a volunteer experience entry]",
                'html': "VOLUNTEER -> <p class=\"volunteer\">",
                'style': ".volunteer -> small text, muted, professional",
            },
            {
                'name': 'languages',
                'content': "LANGUAGES: [title]\n- [language]\n- [language]",
                'html': "LANGUAGES -> <div class=\"languages\"> with <h3> and <ul>",
                'style': ".languages -> small text, bordered, clean",
            },
            {
                'name': 'interests',
                'content': "INTERESTS: [title]\n- [interest]\n- [interest]",
                'html': "INTERESTS -> <div class=\"interests\"> with <h3> and <ul>",
                'style': ".interests -> small text, bordered, playful",
            },
            {
                'name': 'signature',
                'content': "SIGNATURE: [a 'sincerely' sign-off]",
                'html': "SIGNATURE -> <p class=\"signature\">",
                'style': ".signature -> script font, centered, formal",
            },
            {
                'name': 'headline',
                'content': "HEADLINE: [a LinkedIn-style headline]",
                'html': "HEADLINE -> <p class=\"headline\">",
                'style': ".headline -> bold, centered, professional",
            },
        ],
    },
    'group_chat': {
        'name': 'group chat',
        'content_styles': [
            (
                "Write like a chaotic group chat about the topic. Message bubbles, "
                "timestamps, reactions, and escalating drama. Voice is casual, fragmented, "
                "and increasingly unhinged."
            ),
            (
                "Write like a Discord server about the topic. Usernames, message "
                "bubbles, emoji reactions, and a mod warning. Voice is gamer-casual "
                "and escalating."
            ),
            (
                "Write like a family group chat about the topic. Message bubbles, "
                "reactions, forwarded chain messages, and a 'who is this?' moment. "
                "Voice is warm and chaotic."
            ),
        ],
        'layouts': [
            (
                "Build a chat log: a chat header, message bubbles alternating left and right "
                "with names and timestamps, reaction rows, and a typing indicator at the end. "
                "One continuous conversation."
            ),
            (
                "Build a Discord log: a server header, message blocks with usernames, "
                "emoji reactions, and a pinned message. One continuous conversation."
            ),
            (
                "Build a family chat: a group header, message bubbles, reactions, "
                "and forwarded messages. One continuous conversation."
            ),
        ],
        'themes': [
            (
                "Chat look: light gray background, blue and green message bubbles, dark text, "
                "small timestamps, and a phone-app feel. Unified and modern."
            ),
            (
                "Discord look: dark background, colored username accents, message "
                "blocks, and a modern sans-serif. Unified and gamer."
            ),
            (
                "iMessage look: white background, blue and green bubbles, and a "
                "clean sans-serif. Unified and familiar."
            ),
        ],
        'image_ranges': [(0, 1), (0, 2), (1, 2)],
        'elements': [
            {
                'name': 'message_bubble',
                'content': "MESSAGE: [sender]: [message text]",
                'html': "MESSAGE -> <div class=\"message-bubble\"> with <p>",
                'style': ".message-bubble -> rounded bubble, blue/green, sender name",
            },
            {
                'name': 'reaction',
                'content': "REACTION: [emoji reaction to a message]",
                'html': "REACTION -> <p class=\"reaction\">",
                'style': ".reaction -> small emoji row, muted, chat feel",
            },
            {
                'name': 'timestamp',
                'content': "TIMESTAMP: [a chat timestamp]",
                'html': "TIMESTAMP -> <p class=\"timestamp\">",
                'style': ".timestamp -> tiny text, muted, centered",
            },
            {
                'name': 'typing_indicator',
                'content': "TYPING: [a 'typing...' indicator]",
                'html': "TYPING -> <p class=\"typing-indicator\">",
                'style': ".typing-indicator -> animated dots, muted, chat feel",
            },
            {
                'name': 'mod_warning',
                'content': "MODWARNING: [a moderator warning in the chat]",
                'html': "MODWARNING -> <div class=\"mod-warning\"> with <p>",
                'style': ".mod-warning -> red box, bold, urgent",
            },
            {
                'name': 'pinned_message',
                'content': "PINNED: [a pinned message in the chat]",
                'html': "PINNED -> <div class=\"pinned-message\"> with <p>",
                'style': ".pinned-message -> bordered, pin icon, highlighted",
            },
            {
                'name': 'forwarded',
                'content': "FORWARDED: [a forwarded chain message]",
                'html': "FORWARDED -> <div class=\"forwarded\"> with <p>",
                'style': ".forwarded -> italic, bordered, chain feel",
            },
            {
                'name': 'username',
                'content': "USERNAME: [a chat username with a role color]",
                'html': "USERNAME -> <p class=\"username\">",
                'style': ".username -> bold, colored, chat feel",
            },
            {
                'name': 'voice_note',
                'content': "VOICENOTE: [a 'voice note' transcript]",
                'html': "VOICENOTE -> <div class=\"voice-note\"> with <p>",
                'style': ".voice-note -> bordered, mic icon, chat feel",
            },
            {
                'name': 'image_share',
                'content': "IMAGESHARE: [a shared image in the chat]",
                'html': "IMAGESHARE -> <figure class=\"image-share\"> with <img> and <figcaption>",
                'style': ".image-share -> rounded frame, chat feel",
            },
            {
                'name': 'group_name',
                'content': "GROUPNAME: [the group chat name]",
                'html': "GROUPNAME -> <h2 class=\"group-name\">",
                'style': ".group-name -> bold, centered, chat header",
            },
            {
                'name': 'member_join',
                'content': "JOIN: [a 'X joined the chat' line]",
                'html': "JOIN -> <p class=\"member-join\">",
                'style': ".member-join -> small text, centered, muted",
            },
            {
                'name': 'drama_escalation',
                'content': "DRAMA: [an escalating dramatic message]",
                'html': "DRAMA -> <p class=\"drama-escalation\">",
                'style': ".drama-escalation -> bold, red accent, escalating",
            },
            {
                'name': 'who_is_this',
                'content': "WHOIS: [a 'who is this?' moment in the chat]",
                'html': "WHOIS -> <p class=\"who-is-this\">",
                'style': ".who-is-this -> italic, muted, confused",
            },
        ],
    },
    'email_chain': {
        'name': 'email chain',
        'content_styles': [
            (
                "Write like a corporate email chain about the topic. Threaded replies, "
                "escalating subject lines, 'RE: RE: RE:', and passive-aggressive sign-offs. "
                "Voice is corporate and increasingly desperate."
            ),
            (
                "Write like a support ticket thread about the topic. A customer "
                "complaint, agent replies, escalation, and a resolution. Voice is "
                "frustrated and bureaucratic."
            ),
            (
                "Write like a newsletter thread about the topic. A subject line, "
                "a 'you're receiving this because' note, content, and an unsubscribe "
                "footer. Voice is corporate and chipper."
            ),
        ],
        'layouts': [
            (
                "Build an email thread: a subject header, then indented reply blocks each "
                "with a sender, timestamp, and body. Replies nest deeper as the chain "
                "escalates. One continuous thread."
            ),
            (
                "Build a ticket thread: a ticket header, a complaint, agent replies, "
                "and a resolution. Replies nest as one thread."
            ),
            (
                "Build a newsletter: a subject header, a 'you're receiving this' "
                "note, content sections, and an unsubscribe footer. One continuous "
                "email."
            ),
        ],
        'themes': [
            (
                "Email look: white background, gray reply blocks with increasing indentation, "
                "blue links, a red 'RE:' accent, and a corporate sans-serif. Unified and "
                "bureaucratic."
            ),
            (
                "Ticket look: white background, gray reply blocks, a red 'OPEN' "
                "badge, and a monospace ticket number. Unified and support-y."
            ),
            (
                "Newsletter look: white background, a bold header, content sections, "
                "and a gray footer. Unified and corporate."
            ),
        ],
        'image_ranges': [(0, 1), (0, 2), (1, 2)],
        'elements': [
            {
                'name': 'reply_block',
                'content': "REPLY: [sender]: [reply text]",
                'html': "REPLY -> <div class=\"reply-block\"> with <p>",
                'style': ".reply-block -> indented, gray background, email feel",
            },
            {
                'name': 'subject_line',
                'content': "SUBJECT: [an escalating subject line]",
                'html': "SUBJECT -> <h2 class=\"subject-line\">",
                'style': ".subject-line -> bold, red RE: accent, email feel",
            },
            {
                'name': 'sign_off',
                'content': "SIGNOFF: [a passive-aggressive sign-off]",
                'html': "SIGNOFF -> <p class=\"sign-off\">",
                'style': ".sign-off -> italic, muted, corporate",
            },
            {
                'name': 'attachment',
                'content': "ATTACHMENT: [a fake attachment name]",
                'html': "ATTACHMENT -> <p class=\"attachment\">",
                'style': ".attachment -> small text, paperclip icon, muted",
            },
            {
                'name': 'cc_list',
                'content': "CC: [a list of absurd CC'd people]",
                'html': "CC -> <p class=\"cc-list\">",
                'style': ".cc-list -> small text, muted, email feel",
            },
            {
                'name': 'forwarded_email',
                'content': "FORWARDED: [a forwarded email chain]",
                'html': "FORWARDED -> <div class=\"forwarded-email\"> with <p>",
                'style': ".forwarded-email -> indented, bordered, chain feel",
            },
            {
                'name': 'ticket_number',
                'content': "TICKET: [a fake support ticket number]",
                'html': "TICKET -> <p class=\"ticket-number\">",
                'style': ".ticket-number -> monospace, small, muted",
            },
            {
                'name': 'escalation',
                'content': "ESCALATION: [an escalation notice]",
                'html': "ESCALATION -> <div class=\"escalation\"> with <p>",
                'style': ".escalation -> red box, bold, urgent",
            },
            {
                'name': 'unsubscribe',
                'content': "UNSUBSCRIBE: [an unsubscribe footer]",
                'html': "UNSUBSCRIBE -> <p class=\"unsubscribe\">",
                'style': ".unsubscribe -> tiny text, muted, footer feel",
            },
            {
                'name': 'greeting',
                'content': "GREETING: [a corporate email greeting]",
                'html': "GREETING -> <p class=\"greeting\">",
                'style': ".greeting -> small text, muted, email feel",
            },
            {
                'name': 'thread_depth',
                'content': "THREAD: [a 'RE: RE: RE:' depth indicator]",
                'html': "THREAD -> <p class=\"thread-depth\">",
                'style': ".thread-depth -> small text, red, escalating",
            },
            {
                'name': 'auto_reply',
                'content': "AUTOREPLY: [an auto-reply message]",
                'html': "AUTOREPLY -> <div class=\"auto-reply\"> with <p>",
                'style': ".auto-reply -> italic, bordered, robotic",
            },
            {
                'name': 'email_footer',
                'content': "EMAILFOOTER: [a corporate email footer]",
                'html': "EMAILFOOTER -> <p class=\"email-footer\">",
                'style': ".email-footer -> tiny text, muted, legal feel",
            },
            {
                'name': 'resolved',
                'content': "RESOLVED: [a 'ticket resolved' notice]",
                'html': "RESOLVED -> <p class=\"resolved\">",
                'style': ".resolved -> green text, bold, official",
            },
        ],
    },
    'stock_ticker': {
        'name': 'stock ticker',
        'content_styles': [
            (
                "Write like a financial report about the topic. Ticker symbols, prices, "
                "up/down arrows, and analyst notes. Voice is Wall Street confident and "
                "absurdly specific about nonsense stocks."
            ),
            (
                "Write like a market newsletter. A market summary, ticker symbols, "
                "analyst notes, and a 'what to watch' section. Voice is confident "
                "and jargon-heavy."
            ),
            (
                "Write like a day-trader's journal. Ticker symbols, prices, trades, "
                "and a 'lessons learned' section. Voice is manic and self-important."
            ),
        ],
        'layouts': [
            (
                "Build a market page: a scrolling ticker header, a table of ticker symbols "
                "with prices and arrows, analyst note cards, and a market summary footer. "
                "One continuous financial document."
            ),
            (
                "Build a newsletter: a market summary header, a ticker table, analyst "
                "notes, and a 'what to watch' section. One continuous document."
            ),
            (
                "Build a journal: a header, a trades table, a 'lessons learned' "
                "list, and a summary. One continuous document."
            ),
        ],
        'themes': [
            (
                "Finance look: dark background, green and red price accents, monospace "
                "numbers, white text, and a terminal feel. Unified and high-stakes."
            ),
            (
                "Bloomberg look: dark blue background, green and red accents, "
                "monospace numbers, and a clean sans-serif. Unified and professional."
            ),
            (
                "Journal look: white background, green and red accents, a trades "
                "table, and a monospace font. Unified and personal."
            ),
        ],
        'image_ranges': [(0, 1), (0, 2), (1, 2)],
        'elements': [
            {
                'name': 'ticker_symbol',
                'content': "TICKER: [symbol]: [price] [up/down arrow]",
                'html': "TICKER -> <p class=\"ticker-symbol\">",
                'style': ".ticker-symbol -> monospace, green/red, bold",
            },
            {
                'name': 'analyst_note',
                'content': "ANALYST: [an analyst's absurd note]",
                'html': "ANALYST -> <blockquote class=\"analyst-note\"> with <cite>",
                'style': ".analyst-note -> italic, bordered, professional",
            },
            {
                'name': 'market_summary',
                'content': "MARKET: [a market summary paragraph]",
                'html': "MARKET -> <p class=\"market-summary\">",
                'style': ".market-summary -> bold, centered, financial",
            },
            {
                'name': 'price_table',
                'content': "PRICETABLE: [title]\n- [symbol]: [price]\n- [symbol]: [price]",
                'html': "PRICETABLE -> <table class=\"price-table\"> with <thead>/<tbody>",
                'style': ".price-table -> striped rows, green/red, monospace",
            },
            {
                'name': 'what_to_watch',
                'content': "WATCH: [a 'what to watch' section]",
                'html': "WATCH -> <section class=\"what-to-watch\"> with <h2> and <p>",
                'style': ".what-to-watch -> standard section, bold heading",
            },
            {
                'name': 'trade_log',
                'content': "TRADE: [a day-trader's trade entry]",
                'html': "TRADE -> <p class=\"trade-log\">",
                'style': ".trade-log -> monospace, bordered, journal feel",
            },
            {
                'name': 'lessons_learned',
                'content': "LESSONS: [title]\n- [lesson]\n- [lesson]",
                'html': "LESSONS -> <div class=\"lessons-learned\"> with <h3> and <ul>",
                'style': ".lessons-learned -> bordered, bold, reflective",
            },
            {
                'name': 'ticker_tape',
                'content': "TAPELINE: [a scrolling ticker tape line]",
                'html': "TAPELINE -> <p class=\"ticker-tape\">",
                'style': ".ticker-tape -> monospace, scrolling feel, muted",
            },
            {
                'name': 'risk_disclaimer',
                'content': "RISK: [a 'not financial advice' disclaimer]",
                'html': "RISK -> <p class=\"risk-disclaimer\">",
                'style': ".risk-disclaimer -> tiny text, muted, legal feel",
            },
            {
                'name': 'portfolio',
                'content': "PORTFOLIO: [title]\n- [holding]: [value]\n- [holding]: [value]",
                'html': "PORTFOLIO -> <div class=\"portfolio\"> with <h3> and <ul>",
                'style': ".portfolio -> bordered, monospace, financial",
            },
            {
                'name': 'earnings_call',
                'content': "EARNINGS: [an earnings call transcript excerpt]",
                'html': "EARNINGS -> <blockquote class=\"earnings-call\"> with <cite>",
                'style': ".earnings-call -> italic, bordered, corporate",
            },
            {
                'name': 'market_alert',
                'content': "ALERT: [a market alert]",
                'html': "ALERT -> <div class=\"market-alert\"> with <p>",
                'style': ".market-alert -> red box, bold, urgent",
            },
            {
                'name': 'dividend',
                'content': "DIVIDEND: [a dividend announcement]",
                'html': "DIVIDEND -> <p class=\"dividend\">",
                'style': ".dividend -> small text, muted, financial",
            },
            {
                'name': 'closing_bell',
                'content': "CLOSING: [a 'closing bell' summary]",
                'html': "CLOSING -> <p class=\"closing-bell\">",
                'style': ".closing-bell -> bold, centered, dramatic",
            },
        ],
    },
    'weather_report': {
        'name': 'weather report',
        'content_styles': [
            (
                "Write like a weather forecast about the topic. Forecast cards, advisories, "
                "and a radar description. Voice is meteorologist-cheerful and absurdly "
                "specific about the topic's 'conditions'."
            ),
            (
                "Write like a storm-chaser's report. A 'conditions are brewing' "
                "framing, a radar description, a warning, and a 'stay safe' note. "
                "Voice is dramatic and urgent."
            ),
            (
                "Write like a weekly forecast. Day-by-day cards, a 'looking ahead' "
                "section, and a 'dress accordingly' note. Voice is friendly and "
                "practical."
            ),
        ],
        'layouts': [
            (
                "Build a forecast page: a weather header, a big current-conditions card, a "
                "grid of forecast day cards, an advisory box, and a radar image slot. One "
                "continuous forecast."
            ),
            (
                "Build a storm report: a header, a radar image slot, a conditions "
                "section, a warning box, and a 'stay safe' note. One continuous "
                "report."
            ),
            (
                "Build a weekly forecast: a header, day cards, a 'looking ahead' "
                "section, and a footer note. One continuous forecast."
            ),
        ],
        'themes': [
            (
                "Weather look: sky blue background, white cards, sun and cloud accents, "
                "bold temperature numbers, and a clean sans-serif. Unified and breezy."
            ),
            (
                "Storm look: dark gray background, yellow warning accents, bold "
                "text, and a dramatic sans-serif. Unified and urgent."
            ),
            (
                "Morning show look: light blue background, white cards, bold "
                "numbers, and a friendly sans-serif. Unified and bright."
            ),
        ],
        'image_ranges': [(2, 3), (1, 3), (2, 4)],
        'elements': [
            {
                'name': 'forecast_card',
                'content': "FORECAST: [day]: [condition], [temp]",
                'html': "FORECAST -> <div class=\"forecast-card\"> with <h3> and <p>",
                'style': ".forecast-card -> white card, sun/cloud icon, bold temp",
            },
            {
                'name': 'advisory',
                'content': "ADVISORY: [a weather advisory]",
                'html': "ADVISORY -> <div class=\"advisory\"> with <p>",
                'style': ".advisory -> yellow box, bold border, warning",
            },
            {
                'name': 'radar',
                'content': "RADAR: [a radar description]",
                'html': "RADAR -> <div class=\"radar\"> with <p>",
                'style': ".radar -> bordered, green/blue, map feel",
            },
            {
                'name': 'current_conditions',
                'content': "CURRENT: [current conditions: temp, condition]",
                'html': "CURRENT -> <div class=\"current-conditions\"> with <p>",
                'style': ".current-conditions -> big card, huge temp, bold",
            },
            {
                'name': 'looking_ahead',
                'content': "AHEAD: [a 'looking ahead' forecast]",
                'html': "AHEAD -> <section class=\"looking-ahead\"> with <h2> and <p>",
                'style': ".looking-ahead -> standard section, bold heading",
            },
            {
                'name': 'dress_accordingly',
                'content': "DRESS: [a 'dress accordingly' note]",
                'html': "DRESS -> <p class=\"dress-accordingly\">",
                'style': ".dress-accordingly -> small text, muted, friendly",
            },
            {
                'name': 'storm_warning',
                'content': "STORM: [a storm warning]",
                'html': "STORM -> <div class=\"storm-warning\"> with <p>",
                'style': ".storm-warning -> red box, bold, urgent",
            },
            {
                'name': 'stay_safe',
                'content': "STAYSAFE: [a 'stay safe' note]",
                'html': "STAYSAFE -> <p class=\"stay-safe\">",
                'style': ".stay-safe -> italic, centered, caring",
            },
            {
                'name': 'humidity',
                'content': "HUMIDITY: [a humidity reading]",
                'html': "HUMIDITY -> <p class=\"humidity\">",
                'style': ".humidity -> small text, muted, data feel",
            },
            {
                'name': 'wind',
                'content': "WIND: [a wind reading]",
                'html': "WIND -> <p class=\"wind\">",
                'style': ".wind -> small text, muted, data feel",
            },
            {
                'name': 'uv_index',
                'content': "UV: [a UV index reading]",
                'html': "UV -> <p class=\"uv-index\">",
                'style': ".uv-index -> small text, colored, data feel",
            },
            {
                'name': 'weekend_outlook',
                'content': "WEEKEND: [a weekend outlook]",
                'html': "WEEKEND -> <p class=\"weekend-outlook\">",
                'style': ".weekend-outlook -> italic, centered, friendly",
            },
            {
                'name': 'weather_alert',
                'content': "WEATHERALERT: [a weather alert banner]",
                'html': "WEATHERALERT -> <div class=\"weather-alert\"> with <p>",
                'style': ".weather-alert -> red banner, all-caps, urgent",
            },
            {
                'name': 'meteorologist_note',
                'content': "METEOROLOGIST: [a note from the 'meteorologist']",
                'html': "METEOROLOGIST -> <blockquote class=\"meteorologist-note\"> with <cite>",
                'style': ".meteorologist-note -> italic, bordered, cheerful",
            },
        ],
    },
    'dating_profile': {
        'name': 'dating profile',
        'content_styles': [
            (
                "Write like a dating app profile for the topic. Bio, dealbreakers, "
                "'swipe energy', and a prompt answer. Voice is trying-too-hard, quirky, "
                "and absurdly self-aware."
            ),
            (
                "Write like a dating profile that has been up too long. A bio, "
                "dealbreakers, a 'what I'm looking for' section, and a prompt answer. "
                "Voice is desperate and funny."
            ),
            (
                "Write like a matchmaker's profile for the topic. A 'client' bio, "
                "a 'perfect match' description, dealbreakers, and a 'contact me' "
                "note. Voice is professional and slightly pushy."
            ),
        ],
        'layouts': [
            (
                "Build a dating profile: a profile header with a photo slot, a bio section, "
                "a dealbreakers list, a prompt answer, and a swipe-action footer. One "
                "continuous profile card."
            ),
            (
                "Build a profile: a header with a photo slot, a bio, a 'what I'm "
                "looking for' section, dealbreakers, and a prompt answer. One card."
            ),
            (
                "Build a matchmaker profile: a header, a client bio, a 'perfect "
                "match' section, dealbreakers, and a contact note. One card."
            ),
        ],
        'themes': [
            (
                "Dating app look: white background, a single bold accent color (pink or "
                "orange), rounded cards, photo frames, and a modern sans-serif. Unified and "
                "flirty."
            ),
            (
                "Matchmaker look: cream background, gold accents, a formal serif, "
                "and a bordered card. Unified and professional."
            ),
            (
                "Minimal look: white background, black text, a single accent, and "
                "lots of whitespace. Unified and clean."
            ),
        ],
        'image_ranges': [(2, 3), (1, 3), (2, 4)],
        'elements': [
            {
                'name': 'bio',
                'content': "BIO: [a trying-too-hard dating bio]",
                'html': "BIO -> <p class=\"bio\">",
                'style': ".bio -> italic, centered, flirty",
            },
            {
                'name': 'dealbreakers',
                'content': "DEALBREAKERS: [title]\n- [dealbreaker]\n- [dealbreaker]",
                'html': "DEALBREAKERS -> <div class=\"dealbreakers\"> with <h3> and <ul>",
                'style': ".dealbreakers -> bordered, bold, red accents",
            },
            {
                'name': 'prompt_answer',
                'content': "PROMPT: [a dating prompt answer]",
                'html': "PROMPT -> <p class=\"prompt-answer\">",
                'style': ".prompt-answer -> italic, bordered, playful",
            },
            {
                'name': 'swipe_energy',
                'content': "SWIPE: [a 'swipe energy' line]",
                'html': "SWIPE -> <p class=\"swipe-energy\">",
                'style': ".swipe-energy -> bold, centered, flirty",
            },
            {
                'name': 'what_looking_for',
                'content': "LOOKINGFOR: [a 'what I'm looking for' section]",
                'html': "LOOKINGFOR -> <p class=\"what-looking-for\">",
                'style': ".what-looking-for -> italic, centered, hopeful",
            },
            {
                'name': 'photo_caption',
                'content': "PHOTOCAP: [a caption for a profile photo]",
                'html': "PHOTOCAP -> <figcaption class=\"photo-caption\">",
                'style': ".photo-caption -> small text, muted, playful",
            },
            {
                'name': 'fun_fact',
                'content': "FUNFACT: [a 'fun fact about me' line]",
                'html': "FUNFACT -> <p class=\"fun-fact\">",
                'style': ".fun-fact -> small text, italic, playful",
            },
            {
                'name': 'ideal_first_date',
                'content': "FIRSTDATE: [an 'ideal first date' description]",
                'html': "FIRSTDATE -> <p class=\"ideal-first-date\">",
                'style': ".ideal-first-date -> italic, centered, romantic",
            },
            {
                'name': 'green_flags',
                'content': "GREENFLAGS: [title]\n- [green flag]\n- [green flag]",
                'html': "GREENFLAGS -> <div class=\"green-flags\"> with <h3> and <ul>",
                'style': ".green-flags -> bordered, green accents, positive",
            },
            {
                'name': 'red_flags',
                'content': "REDFLAGS: [title]\n- [red flag]\n- [red flag]",
                'html': "REDFLAGS -> <div class=\"red-flags\"> with <h3> and <ul>",
                'style': ".red-flags -> bordered, red accents, warning",
            },
            {
                'name': 'matchmaker_note',
                'content': "MATCHMAKER: [a matchmaker's note about the topic]",
                'html': "MATCHMAKER -> <blockquote class=\"matchmaker-note\"> with <cite>",
                'style': ".matchmaker-note -> italic, bordered, professional",
            },
            {
                'name': 'contact_me',
                'content': "CONTACTME: [a 'contact me' line]",
                'html': "CONTACTME -> <p class=\"contact-me\">",
                'style': ".contact-me -> bold, centered, flirty",
            },
            {
                'name': 'relationship_goals',
                'content': "GOALS: [a 'relationship goals' line]",
                'html': "GOALS -> <p class=\"relationship-goals\">",
                'style': ".relationship-goals -> italic, centered, hopeful",
            },
            {
                'name': 'profile_prompt',
                'content': "PROFILEPROMPT: [a 'two truths and a lie' prompt]",
                'html': "PROFILEPROMPT -> <p class=\"profile-prompt\">",
                'style': ".profile-prompt -> italic, bordered, playful",
            },
        ],
    },
    'dictionary_entry': {
        'name': 'dictionary entry',
        'content_styles': [
            (
                "Write like a dictionary entry for the topic. Pronunciation, part of speech, "
                "definition, usage example, and etymology. Voice is lexicographer-dry and "
                "absurdly precise about nonsense."
            ),
            (
                "Write like an urban dictionary entry. A word, a definition, a "
                "usage example, and a 'tags' line. Voice is casual and funny."
            ),
            (
                "Write like a thesaurus entry. A word, synonyms, antonyms, and a "
                "usage note. Voice is dry and precise."
            ),
        ],
        'layouts': [
            (
                "Build a dictionary page: a header with the word and pronunciation, a "
                "definition section, a usage example, an etymology note, and related words. "
                "Single column, reference-book layout."
            ),
            (
                "Build an entry: a header, a definition, a usage example, a "
                "'tags' line, and a 'vote' note. Single column, casual."
            ),
            (
                "Build a thesaurus page: a header, synonyms, antonyms, and a usage "
                "note. Single column, reference layout."
            ),
        ],
        'themes': [
            (
                "Dictionary look: white background, black serif text, a bold entry word, "
                "small pronunciation marks, and thin rules. Unified and reference-like."
            ),
            (
                "Urban dictionary look: white background, black text, a bold "
                "accent color, and a casual sans-serif. Unified and modern."
            ),
            (
                "Thesaurus look: white background, black serif text, a single "
                "accent color, and thin rules. Unified and reference-like."
            ),
        ],
        'image_ranges': [(0, 1), (0, 2), (1, 2)],
        'elements': [
            {
                'name': 'pronunciation',
                'content': "PRONUNCIATION: [a phonetic pronunciation]",
                'html': "PRONUNCIATION -> <p class=\"pronunciation\">",
                'style': ".pronunciation -> small text, phonetic marks, muted",
            },
            {
                'name': 'definition',
                'content': "DEFINITION: [a precise absurd definition]",
                'html': "DEFINITION -> <p class=\"definition\">",
                'style': ".definition -> serif, bold entry word, reference feel",
            },
            {
                'name': 'usage_example',
                'content': "USAGE: [a usage example sentence]",
                'html': "USAGE -> <p class=\"usage-example\">",
                'style': ".usage-example -> italic, indented, reference feel",
            },
            {
                'name': 'etymology',
                'content': "ETYMOLOGY: [a fake etymology]",
                'html': "ETYMOLOGY -> <p class=\"etymology\">",
                'style': ".etymology -> small text, muted, reference feel",
            },
            {
                'name': 'part_of_speech',
                'content': "POS: [part of speech]",
                'html': "POS -> <p class=\"part-of-speech\">",
                'style': ".part-of-speech -> small italic text, muted",
            },
            {
                'name': 'synonyms',
                'content': "SYNONYMS: [title]\n- [synonym]\n- [synonym]",
                'html': "SYNONYMS -> <div class=\"synonyms\"> with <h3> and <ul>",
                'style': ".synonyms -> small text, bordered, reference feel",
            },
            {
                'name': 'antonyms',
                'content': "ANTONYMS: [title]\n- [antonym]\n- [antonym]",
                'html': "ANTONYMS -> <div class=\"antonyms\"> with <h3> and <ul>",
                'style': ".antonyms -> small text, bordered, reference feel",
            },
            {
                'name': 'related_words',
                'content': "RELATED: [title]\n- [related word]\n- [related word]",
                'html': "RELATED -> <div class=\"related-words\"> with <h3> and <ul>",
                'style': ".related-words -> small text, bordered, reference feel",
            },
            {
                'name': 'tags',
                'content': "TAGS: [title]\n- [tag]\n- [tag]",
                'html': "TAGS -> <div class=\"tags\"> with <h3> and <ul>",
                'style': ".tags -> small gray tags, bordered, casual",
            },
            {
                'name': 'vote_note',
                'content': "VOTE: [a 'vote on this definition' note]",
                'html': "VOTE -> <p class=\"vote-note\">",
                'style': ".vote-note -> small text, muted, casual",
            },
            {
                'name': 'word_of_day',
                'content': "WOTD: [a 'word of the day' banner]",
                'html': "WOTD -> <div class=\"word-of-day\"> with <p>",
                'style': ".word-of-day -> bold, centered, accent color",
            },
            {
                'name': 'cross_reference',
                'content': "CROSSREF: [a 'see also' cross-reference]",
                'html': "CROSSREF -> <p class=\"cross-reference\">",
                'style': ".cross-reference -> small text, blue link, muted",
            },
        ],
    },
    'bingo_card': {
        'name': 'bingo card',
        'content_styles': [
            (
                "Write like a bingo card about the topic. A 3x3 grid of phrases, a free "
                "space, and a caller's commentary. Voice is game-night energetic and absurd."
            ),
            (
                "Write like a buzzword bingo card. A grid of corporate phrases, a "
                "free space, and a 'how to play' note. Voice is dry and funny."
            ),
            (
                "Write like a drinking-game bingo card. A grid of phrases, a free "
                "space, and a 'rules' note. Voice is rowdy and fun."
            ),
        ],
        'layouts': [
            (
                "Build a bingo card: a BINGO header, a 3x3 grid table with phrases and a "
                "center FREE space, and a caller's note below. One compact card."
            ),
            (
                "Build a bingo card: a header, a 3x3 grid table, a 'how to play' "
                "note, and a footer. One compact card."
            ),
            (
                "Build a bingo card: a header, a 3x3 grid table, a 'rules' note, "
                "and a footer. One compact card."
            ),
        ],
        'themes': [
            (
                "Bingo look: white background, red and blue accents, a bold BINGO header, "
                "bordered grid cells, and a festive feel. Unified and game-night."
            ),
            (
                "Corporate bingo look: white background, gray and blue accents, "
                "a clean grid, and a sans-serif. Unified and office-y."
            ),
            (
                "Party bingo look: bright background, bold colors, a festive "
                "header, and bordered cells. Unified and rowdy."
            ),
        ],
        'image_ranges': [(0, 1), (0, 2), (1, 2)],
        'elements': [
            {
                'name': 'bingo_grid',
                'content': "BINGOGRID: [title]\n- [phrase]\n- [phrase]\n- [phrase]\n- [phrase]\n- [phrase]\n- [phrase]\n- [phrase]\n- [phrase]",
                'html': "BINGOGRID -> <table class=\"bingo-grid\"> with <tbody> of cells",
                'style': ".bingo-grid -> 3x3 grid, bordered cells, festive",
            },
            {
                'name': 'free_space',
                'content': "FREESPACE: [a 'FREE' center space]",
                'html': "FREESPACE -> <td class=\"free-space\">",
                'style': ".free-space -> bold, centered, star accent",
            },
            {
                'name': 'caller_commentary',
                'content': "CALLER: [a bingo caller's commentary]",
                'html': "CALLER -> <p class=\"caller-commentary\">",
                'style': ".caller-commentary -> italic, centered, game-night",
            },
            {
                'name': 'how_to_play',
                'content': "HOWTOPLAY: [a 'how to play' note]",
                'html': "HOWTOPLAY -> <p class=\"how-to-play\">",
                'style': ".how-to-play -> small text, muted, bordered",
            },
            {
                'name': 'rules',
                'content': "RULES: [title]\n- [rule]\n- [rule]",
                'html': "RULES -> <div class=\"rules\"> with <h3> and <ul>",
                'style': ".rules -> bordered, small text, game-night",
            },
            {
                'name': 'bingo_header',
                'content': "BINGOHEADER: [a BINGO title]",
                'html': "BINGOHEADER -> <h2 class=\"bingo-header\">",
                'style': ".bingo-header -> bold, letter-spaced, festive",
            },
            {
                'name': 'winning_line',
                'content': "WINNING: [a 'winning line' description]",
                'html': "WINNING -> <p class=\"winning-line\">",
                'style': ".winning-line -> bold, green, celebratory",
            },
            {
                'name': 'prize',
                'content': "PRIZE: [a prize for winning]",
                'html': "PRIZE -> <p class=\"prize\">",
                'style': ".prize -> bold, gold, celebratory",
            },
            {
                'name': 'daubed',
                'content': "DAUBED: [a 'daubed' phrase description]",
                'html': "DAUBED -> <p class=\"daubed\">",
                'style': ".daubed -> strikethrough, muted, game feel",
            },
            {
                'name': 'bingo_call',
                'content': "BINGOCALL: [a dramatic 'BINGO!' call]",
                'html': "BINGOCALL -> <p class=\"bingo-call\">",
                'style': ".bingo-call -> huge bold text, centered, celebratory",
            },
            {
                'name': 'card_number',
                'content': "CARDNUM: [a bingo card number]",
                'html': "CARDNUM -> <p class=\"card-number\">",
                'style': ".card-number -> small text, muted, corner",
            },
            {
                'name': 'round_note',
                'content': "ROUND: [a 'round X' note]",
                'html': "ROUND -> <p class=\"round-note\">",
                'style': ".round-note -> small text, centered, muted",
            },
        ],
    },
    'tournament_bracket': {
        'name': 'tournament bracket',
        'content_styles': [
            (
                "Write like a tournament bracket about the topic. Matchups, upsets, and a "
                "champion. Voice is sports-announcer hype and absurdly invested in nonsense "
                "contenders."
            ),
            (
                "Write like a sports column about the topic. A 'the field is wide "
                "open' framing, matchups, a dark horse pick, and a champion prediction. "
                "Voice is confident and dramatic."
            ),
            (
                "Write like a fantasy draft guide. A draft order, picks, a 'steal "
                "of the draft' note, and a champion pick. Voice is analytical and "
                "hype."
            ),
        ],
        'layouts': [
            (
                "Build a bracket: a header, then rounds of matchups laid out as a bracket "
                "tree, with a champion box at the end. Matchups flow down the page as one "
                "tournament."
            ),
            (
                "Build a bracket: a header, matchup sections, a dark horse box, "
                "and a champion box. Flows as one tournament."
            ),
            (
                "Build a draft board: a header, a draft order list, pick sections, "
                "and a champion box. One continuous board."
            ),
        ],
        'themes': [
            (
                "Bracket look: dark background, neon accent lines connecting matchups, bold "
                "white text, and a champion highlight. Unified and competitive."
            ),
            (
                "Sports column look: white background, bold headings, a single "
                "accent color, and a clean sans-serif. Unified and editorial."
            ),
            (
                "Draft look: dark background, team-color accents, a draft board, "
                "and a bold sans-serif. Unified and analytical."
            ),
        ],
        'image_ranges': [(0, 1), (0, 2), (1, 2)],
        'elements': [
            {
                'name': 'matchup',
                'content': "MATCHUP: [contender A] vs [contender B]",
                'html': "MATCHUP -> <div class=\"matchup\"> with two <p> blocks and a vs divider",
                'style': ".matchup -> two-column, versus divider, bold",
            },
            {
                'name': 'upset',
                'content': "UPSET: [a 'shocking upset' description]",
                'html': "UPSET -> <p class=\"upset\">",
                'style': ".upset -> bold, red accent, dramatic",
            },
            {
                'name': 'champion',
                'content': "CHAMPION: [the champion]",
                'html': "CHAMPION -> <div class=\"champion\"> with <p>",
                'style': ".champion -> gold box, bold, celebratory",
            },
            {
                'name': 'dark_horse',
                'content': "DARKHORSE: [a 'dark horse' pick]",
                'html': "DARKHORSE -> <p class=\"dark-horse\">",
                'style': ".dark-horse -> italic, muted, underdog feel",
            },
            {
                'name': 'round_label',
                'content': "ROUND: [a 'round X' label]",
                'html': "ROUND -> <h3 class=\"round-label\">",
                'style': ".round-label -> bold, centered, bracket feel",
            },
            {
                'name': 'draft_order',
                'content': "DRAFTORDER: [title]\n1. [pick]\n2. [pick]\n3. [pick]",
                'html': "DRAFTORDER -> <div class=\"draft-order\"> with <h3> and <ol>",
                'style': ".draft-order -> numbered, bold, draft feel",
            },
            {
                'name': 'steal_of_draft',
                'content': "STEAL: [a 'steal of the draft' note]",
                'html': "STEAL -> <p class=\"steal-of-draft\">",
                'style': ".steal-of-draft -> bold, green, celebratory",
            },
            {
                'name': 'announcer_call',
                'content': "ANNOUNCER: [a sports-announcer call]",
                'html': "ANNOUNCER -> <blockquote class=\"announcer-call\"> with <cite>",
                'style': ".announcer-call -> italic, bold, hype",
            },
            {
                'name': 'bracket_line',
                'content': "BRACKETLINE: [a connecting bracket line description]",
                'html': "BRACKETLINE -> <p class=\"bracket-line\">",
                'style': ".bracket-line -> small text, muted, connector feel",
            },
            {
                'name': 'final_four',
                'content': "FINALFOUR: [title]\n- [contender]\n- [contender]\n- [contender]\n- [contender]",
                'html': "FINALFOUR -> <div class=\"final-four\"> with <h3> and <ul>",
                'style': ".final-four -> bordered, bold, bracket feel",
            },
            {
                'name': 'cinderella',
                'content': "CINDERELLA: [a 'Cinderella story' description]",
                'html': "CINDERELLA -> <p class=\"cinderella\">",
                'style': ".cinderella -> italic, warm, underdog feel",
            },
            {
                'name': 'champion_prediction',
                'content': "PREDICTION: [a champion prediction]",
                'html': "PREDICTION -> <p class=\"champion-prediction\">",
                'style': ".champion-prediction -> bold, centered, confident",
            },
            {
                'name': 'bracket_seed',
                'content': "SEED: [a seed number for a contender]",
                'html': "SEED -> <p class=\"bracket-seed\">",
                'style': ".bracket-seed -> small text, muted, bracket feel",
            },
            {
                'name': 'tournament_title',
                'content': "TOURNAMENT: [a tournament title]",
                'html': "TOURNAMENT -> <h2 class=\"tournament-title\">",
                'style': ".tournament-title -> bold, centered, dramatic",
            },
        ],
    },
    'movie_poster': {
        'name': 'movie poster',
        'content_styles': [
            (
                "Write like a movie poster for the topic. Title treatment, tagline, cast "
                "list, and a credits block. Voice is Hollywood-hype and dramatically "
                "overblown about the topic."
            ),
            (
                "Write like a film review for the topic. A star rating, a 'the "
                "verdict' framing, a plot summary, and a 'worth seeing?' note. Voice "
                "is critic-smug and funny."
            ),
            (
                "Write like a trailer voiceover for the topic. 'In a world...' "
                "framing, dramatic beats, a tagline, and a release date. Voice is "
                "deep and overblown."
            ),
        ],
        'layouts': [
            (
                "Build a movie poster: a huge title, a tagline, a large image slot, a cast "
                "list, and a credits block at the bottom. Centered, poster-style, one "
                "dramatic composition."
            ),
            (
                "Build a review: a header with a star rating, a verdict section, "
                "a plot summary, and a 'worth seeing?' note. One continuous review."
            ),
            (
                "Build a trailer page: a huge title, a tagline, an image slot, "
                "a 'in a world' section, and a release date. Centered, dramatic."
            ),
        ],
        'themes': [
            (
                "Poster look: dark cinematic background, bold title treatment, gold or red "
                "accents, a tagline in italics, and a credits block in small caps. Unified "
                "and dramatic."
            ),
            (
                "Review look: white background, black text, a star rating accent, "
                "and a clean sans-serif. Unified and editorial."
            ),
            (
                "Trailer look: dark background, bold white title, a single accent, "
                "and a dramatic serif. Unified and cinematic."
            ),
        ],
        'image_ranges': [(1, 2), (1, 3), (2, 3)],
        'elements': [
            {
                'name': 'title_treatment',
                'content': "TITLETREATMENT: [a dramatic movie title]",
                'html': "TITLETREATMENT -> <h1 class=\"title-treatment\">",
                'style': ".title-treatment -> huge bold title, gold/red, cinematic",
            },
            {
                'name': 'tagline',
                'content': "TAGLINE: [a dramatic tagline]",
                'html': "TAGLINE -> <p class=\"tagline\">",
                'style': ".tagline -> italic, centered, dramatic",
            },
            {
                'name': 'cast_list',
                'content': "CAST: [title]\n- [actor]: [role]\n- [actor]: [role]",
                'html': "CAST -> <div class=\"cast-list\"> with <h3> and <ul>",
                'style': ".cast-list -> small caps, centered, credits feel",
            },
            {
                'name': 'credits_block',
                'content': "CREDITS: [a credits block of absurd names]",
                'html': "CREDITS -> <p class=\"credits-block\">",
                'style': ".credits-block -> tiny text, small caps, centered",
            },
            {
                'name': 'star_rating',
                'content': "STARS: [a star rating for the topic]",
                'html': "STARS -> <p class=\"star-rating\">",
                'style': ".star-rating -> star icons, bold, centered",
            },
            {
                'name': 'verdict',
                'content': "VERDICT: [a critic's verdict]",
                'html': "VERDICT -> <p class=\"verdict\">",
                'style': ".verdict -> bold, centered, editorial",
            },
            {
                'name': 'plot_summary',
                'content': "PLOT: [a plot summary of the topic]",
                'html': "PLOT -> <p class=\"plot-summary\">",
                'style': ".plot-summary -> italic, centered, editorial",
            },
            {
                'name': 'in_a_world',
                'content': "INAWORLD: [a 'in a world...' trailer line]",
                'html': "INAWORLD -> <p class=\"in-a-world\">",
                'style': ".in-a-world -> bold, centered, cinematic",
            },
            {
                'name': 'release_date',
                'content': "RELEASE: [a release date line]",
                'html': "RELEASE -> <p class=\"release-date\">",
                'style': ".release-date -> small text, centered, muted",
            },
            {
                'name': 'worth_seeing',
                'content': "WORTHSEEING: [a 'worth seeing?' note]",
                'html': "WORTHSEEING -> <p class=\"worth-seeing\">",
                'style': ".worth-seeing -> italic, centered, editorial",
            },
            {
                'name': 'director_note',
                'content': "DIRECTOR: [a 'director's note']",
                'html': "DIRECTOR -> <blockquote class=\"director-note\"> with <cite>",
                'style': ".director-note -> italic, bordered, cinematic",
            },
            {
                'name': 'poster_quote',
                'content': "POSTERQUOTE: [a 'critics are raving' quote]",
                'html': "POSTERQUOTE -> <p class=\"poster-quote\">",
                'style': ".poster-quote -> bold, centered, hype",
            },
            {
                'name': 'genre_line',
                'content': "GENRE: [a genre line]",
                'html': "GENRE -> <p class=\"genre-line\">",
                'style': ".genre-line -> small caps, centered, muted",
            },
            {
                'name': 'poster_footer',
                'content': "POSTERFOOTER: [a poster footer line]",
                'html': "POSTERFOOTER -> <p class=\"poster-footer\">",
                'style': ".poster-footer -> tiny text, centered, credits feel",
            },
        ],
    },
    'restaurant_menu': {
        'name': 'restaurant menu',
        'content_styles': [
            (
                "Write like a restaurant menu about the topic. Sections, prices, chef's "
                "specials, and a 'chef recommends' note. Voice is foodie-pretentious and "
                "absurdly descriptive about nonsense dishes."
            ),
            (
                "Write like a diner menu. Sections, prices, a 'daily specials' "
                "board, and a 'home of the' claim. Voice is friendly and greasy."
            ),
            (
                "Write like a tasting-menu restaurant. Courses, prices, a 'chef's "
                "table' note, and a 'pairing' suggestion. Voice is pretentious and "
                "minimal."
            ),
        ],
        'layouts': [
            (
                "Build a menu: a restaurant header, section headings with item lists and "
                "prices, a chef's special box, and a footer note. Two-column menu layout, "
                "one continuous document."
            ),
            (
                "Build a diner menu: a header, sections with items and prices, "
                "a specials board, and a footer. Two-column, continuous."
            ),
            (
                "Build a tasting menu: a header, numbered courses with prices, "
                "a chef's table note, and a pairing suggestion. One continuous "
                "document."
            ),
        ],
        'themes': [
            (
                "Menu look: cream background, dark text, a single accent color (burgundy or "
                "green), serif headings, and a decorative border. Unified and appetizing."
            ),
            (
                "Diner look: bright background, bold colors, a specials board, "
                "and a friendly sans-serif. Unified and greasy."
            ),
            (
                "Fine dining look: dark background, white text, gold accents, "
                "and a minimal serif. Unified and elegant."
            ),
        ],
        'image_ranges': [(1, 2), (1, 3), (2, 3)],
        'elements': [
            {
                'name': 'menu_section',
                'content': "MENUSECTION: [title]\n- [item]: [price]\n- [item]: [price]",
                'html': "MENUSECTION -> <div class=\"menu-section\"> with <h3> and <ul>",
                'style': ".menu-section -> two-column, dotted leaders, prices",
            },
            {
                'name': 'chefs_special',
                'content': "SPECIAL: [a chef's special dish]",
                'html': "SPECIAL -> <div class=\"chefs-special\"> with <p>",
                'style': ".chefs-special -> gold box, bold, featured",
            },
            {
                'name': 'chef_recommends',
                'content': "RECOMMENDS: [a 'chef recommends' note]",
                'html': "RECOMMENDS -> <p class=\"chef-recommends\">",
                'style': ".chef-recommends -> italic, centered, warm",
            },
            {
                'name': 'price_list',
                'content': "PRICELIST: [title]\n- [item]: [price]\n- [item]: [price]",
                'html': "PRICELIST -> <div class=\"price-list\"> with <h3> and <ul>",
                'style': ".price-list -> dotted leaders, prices right-aligned",
            },
            {
                'name': 'daily_specials',
                'content': "DAILY: [a 'daily specials' board]",
                'html': "DAILY -> <div class=\"daily-specials\"> with <p>",
                'style': ".daily-specials -> chalkboard feel, bold, greasy",
            },
            {
                'name': 'home_of',
                'content': "HOMEOF: [a 'home of the' claim]",
                'html': "HOMEOF -> <p class=\"home-of\">",
                'style': ".home-of -> bold, centered, greasy",
            },
            {
                'name': 'tasting_course',
                'content': "COURSE: [a numbered tasting course]",
                'html': "COURSE -> <div class=\"tasting-course\"> with <h3> and <p>",
                'style': ".tasting-course -> numbered, minimal, elegant",
            },
            {
                'name': 'pairing',
                'content': "PAIRING: [a wine pairing suggestion]",
                'html': "PAIRING -> <p class=\"pairing\">",
                'style': ".pairing -> italic, centered, elegant",
            },
            {
                'name': 'menu_footer',
                'content': "MENUFOOTER: [a menu footer note]",
                'html': "MENUFOOTER -> <p class=\"menu-footer\">",
                'style': ".menu-footer -> small text, centered, muted",
            },
            {
                'name': 'allergen_note',
                'content': "ALLERGEN: [an absurd allergen note]",
                'html': "ALLERGEN -> <p class=\"allergen-note\">",
                'style': ".allergen-note -> tiny text, muted, legal feel",
            },
            {
                'name': 'chefs_table',
                'content': "CHEFSTABLE: [a 'chef's table' note]",
                'html': "CHEFSTABLE -> <p class=\"chefs-table\">",
                'style': ".chefs-table -> italic, centered, elegant",
            },
            {
                'name': 'menu_rating',
                'content': "MENURATING: [a rating for the menu]",
                'html': "MENURATING -> <p class=\"menu-rating\">",
                'style': ".menu-rating -> star icons, bold, centered",
            },
            {
                'name': 'signature_dish',
                'content': "SIGNATURE: [a signature dish description]",
                'html': "SIGNATURE -> <p class=\"signature-dish\">",
                'style': ".signature-dish -> bold, centered, featured",
            },
            {
                'name': 'menu_border',
                'content': "MENUBORDER: [a decorative menu border line]",
                'html': "MENUBORDER -> <hr class=\"menu-border\">",
                'style': ".menu-border -> decorative divider, accent color",
            },
        ],
    },
    'travel_brochure': {
        'name': 'travel brochure',
        'content_styles': [
            (
                "Write like a travel brochure about the topic. Destinations, itineraries, "
                "and 'you must visit' calls. Voice is enthusiastic, aspirational, and "
                "absurdly sells the topic as a vacation spot."
            ),
            (
                "Write like a travel blog. A 'day one' framing, destination "
                "highlights, a 'pro tip' box, and a 'you should go' closer. Voice "
                "is excited and personal."
            ),
            (
                "Write like a cruise brochure. A 'set sail' framing, ports of call, "
                "onboard activities, and a 'book now' closer. Voice is polished and "
                "aspirational."
            ),
        ],
        'layouts': [
            (
                "Build a brochure: a destination header, an itinerary list, destination "
                "cards with image slots, and a 'book now' footer. Flows as one glossy "
                "brochure."
            ),
            (
                "Build a travel blog: a header, day sections, destination cards "
                "with image slots, a pro tip box, and a closer. One continuous post."
            ),
            (
                "Build a cruise brochure: a header, ports of call cards, an "
                "activities list, and a 'book now' footer. One glossy document."
            ),
        ],
        'themes': [
            (
                "Brochure look: bright sky and ocean colors, white cards, bold sans-serif "
                "headings, image frames, and a sunny feel. Unified and aspirational."
            ),
            (
                "Blog look: white background, warm accent colors, image cards, "
                "and a clean sans-serif. Unified and personal."
            ),
            (
                "Cruise look: deep blue background, white cards, gold accents, "
                "and a polished sans-serif. Unified and luxurious."
            ),
        ],
        'image_ranges': [(3, 5), (4, 6), (2, 4)],
        'elements': [
            {
                'name': 'destination_card',
                'content': "DESTINATION: [name]\n[description of the 'destination']",
                'html': "DESTINATION -> <div class=\"destination-card\"> with <h3> and <p>",
                'style': ".destination-card -> white card, image frame, sunny",
            },
            {
                'name': 'itinerary',
                'content': "ITINERARY: [title]\n1. [stop]\n2. [stop]\n3. [stop]",
                'html': "ITINERARY -> <div class=\"itinerary\"> with <h3> and <ol>",
                'style': ".itinerary -> numbered, bold, aspirational",
            },
            {
                'name': 'you_must_visit',
                'content': "MUSTVISIT: [a 'you must visit' call]",
                'html': "MUSTVISIT -> <p class=\"you-must-visit\">",
                'style': ".you-must-visit -> bold, centered, enthusiastic",
            },
            {
                'name': 'book_now',
                'content': "BOOKNOW: [a 'book now' closer]",
                'html': "BOOKNOW -> <div class=\"book-now\"> with <p>",
                'style': ".book-now -> bold, centered, accent color",
            },
            {
                'name': 'pro_tip',
                'content': "PROTIP: [a travel pro tip]",
                'html': "PROTIP -> <div class=\"travel-tip\"> with <p>",
                'style': ".travel-tip -> green box, lightbulb, bordered",
            },
            {
                'name': 'day_section',
                'content': "DAY: [a 'day X' travel blog section]",
                'html': "DAY -> <section class=\"day-section\"> with <h2> and <p>",
                'style': ".day-section -> standard section, bold heading",
            },
            {
                'name': 'port_of_call',
                'content': "PORT: [a cruise port of call]",
                'html': "PORT -> <div class=\"port-of-call\"> with <h3> and <p>",
                'style': ".port-of-call -> white card, gold accent, luxurious",
            },
            {
                'name': 'onboard_activity',
                'content': "ACTIVITY: [an onboard cruise activity]",
                'html': "ACTIVITY -> <p class=\"onboard-activity\">",
                'style': ".onboard-activity -> small text, bordered, playful",
            },
            {
                'name': 'set_sail',
                'content': "SETSAIL: [a 'set sail' framing line]",
                'html': "SETSAIL -> <p class=\"set-sail\">",
                'style': ".set-sail -> bold, centered, aspirational",
            },
            {
                'name': 'highlights',
                'content': "HIGHLIGHTS: [title]\n- [highlight]\n- [highlight]",
                'html': "HIGHLIGHTS -> <div class=\"highlights\"> with <h3> and <ul>",
                'style': ".highlights -> bordered, bold, sunny",
            },
            {
                'name': 'you_should_go',
                'content': "SHOULDGO: [a 'you should go' closer]",
                'html': "SHOULDGO -> <p class=\"you-should-go\">",
                'style': ".you-should-go -> italic, centered, personal",
            },
            {
                'name': 'travel_rating',
                'content': "TRAVELRATING: [a rating for the destination]",
                'html': "TRAVELRATING -> <p class=\"travel-rating\">",
                'style': ".travel-rating -> star icons, bold, centered",
            },
            {
                'name': 'packing_list',
                'content': "PACKING: [title]\n- [item]\n- [item]",
                'html': "PACKING -> <div class=\"packing-list\"> with <h3> and <ul>",
                'style': ".packing-list -> bordered, checklist feel, sunny",
            },
            {
                'name': 'brochure_footer',
                'content': "BROCHUREFOOTER: [a brochure footer line]",
                'html': "BROCHUREFOOTER -> <p class=\"brochure-footer\">",
                'style': ".brochure-footer -> small text, centered, muted",
            },
        ],
    },
    'survival_guide': {
        'name': 'survival guide',
        'content_styles': [
            (
                "Write like a survival field manual about the topic. Numbered steps, "
                "protips, and dire warnings. Voice is gruff, practical, and absurdly "
                "serious about surviving the topic."
            ),
            (
                "Write like a wilderness guide. Numbered steps, a 'what you'll "
                "need' list, a warning, and a 'stay calm' note. Voice is calm and "
                "practical."
            ),
            (
                "Write like a zombie-apocalypse guide. Numbered steps, a supply "
                "list, a warning, and a 'last resort' section. Voice is urgent and "
                "deadpan."
            ),
        ],
        'layouts': [
            (
                "Build a field manual: a cover header, numbered sections with steps, "
                "protip callout boxes, a warning section, and a checklist. One continuous "
                "manual."
            ),
            (
                "Build a guide: a cover header, a 'what you'll need' list, "
                "numbered steps, a warning box, and a 'stay calm' note. One "
                "continuous manual."
            ),
            (
                "Build an apocalypse guide: a cover header, numbered steps, a "
                "supply list, a warning, and a 'last resort' section. One continuous "
                "manual."
            ),
        ],
        'themes': [
            (
                "Field manual look: olive and khaki colors, stencil-style headings, "
                "numbered steps, yellow protip boxes, and a rugged feel. Unified and "
                "military."
            ),
            (
                "Wilderness look: forest green and brown, white background, "
                "numbered steps, and a clean sans-serif. Unified and outdoorsy."
            ),
            (
                "Apocalypse look: dark gray background, yellow warning accents, "
                "bold text, and a rugged feel. Unified and urgent."
            ),
        ],
        'image_ranges': [(1, 2), (1, 3), (2, 3)],
        'elements': [
            {
                'name': 'numbered_steps',
                'content': "STEPS: [title]\n1. [step]\n2. [step]\n3. [step]",
                'html': "STEPS -> <div class=\"survival-steps\"> with <h3> and <ol>",
                'style': ".survival-steps -> numbered, bold, rugged",
            },
            {
                'name': 'protip',
                'content': "PROTIP: [a survival pro tip]",
                'html': "PROTIP -> <div class=\"survival-tip\"> with <p>",
                'style': ".survival-tip -> yellow box, bold border, rugged",
            },
            {
                'name': 'dire_warning',
                'content': "WARNING: [a dire survival warning]",
                'html': "WARNING -> <div class=\"dire-warning\"> with <p>",
                'style': ".dire-warning -> red box, bold, urgent",
            },
            {
                'name': 'what_you_need',
                'content': "NEED: [title]\n- [item]\n- [item]",
                'html': "NEED -> <div class=\"what-you-need\"> with <h3> and <ul>",
                'style': ".what-you-need -> bordered, checklist feel, rugged",
            },
            {
                'name': 'stay_calm',
                'content': "STAYCALM: [a 'stay calm' note]",
                'html': "STAYCALM -> <p class=\"stay-calm\">",
                'style': ".stay-calm -> italic, centered, reassuring",
            },
            {
                'name': 'last_resort',
                'content': "LASTRESORT: [a 'last resort' section]",
                'html': "LASTRESORT -> <section class=\"last-resort\"> with <h2> and <p>",
                'style': ".last-resort -> dark box, bold, urgent",
            },
            {
                'name': 'supply_list',
                'content': "SUPPLY: [title]\n- [supply]\n- [supply]",
                'html': "SUPPLY -> <div class=\"supply-list\"> with <h3> and <ul>",
                'style': ".supply-list -> bordered, checklist feel, rugged",
            },
            {
                'name': 'field_note',
                'content': "FIELDNOTE: [a field manual note]",
                'html': "FIELDNOTE -> <p class=\"field-note\">",
                'style': ".field-note -> small text, muted, technical",
            },
            {
                'name': 'survival_checklist',
                'content': "CHECKLIST: [title]\n- [ ] [item]\n- [ ] [item]",
                'html': "CHECKLIST -> <div class=\"survival-checklist\"> with <h3> and <ul>",
                'style': ".survival-checklist -> checkbox items, bordered, rugged",
            },
            {
                'name': 'emergency_contact',
                'content': "EMERGENCY: [an emergency contact line]",
                'html': "EMERGENCY -> <p class=\"emergency-contact\">",
                'style': ".emergency-contact -> bold, centered, urgent",
            },
            {
                'name': 'terrain_note',
                'content': "TERRAIN: [a terrain description]",
                'html': "TERRAIN -> <p class=\"terrain-note\">",
                'style': ".terrain-note -> small text, muted, technical",
            },
            {
                'name': 'survival_rating',
                'content': "SURVIVALRATING: [a survival difficulty rating]",
                'html': "SURVIVALRATING -> <p class=\"survival-rating\">",
                'style': ".survival-rating -> skull icons, bold, rugged",
            },
            {
                'name': 'cover_header',
                'content': "COVER: [a field manual cover title]",
                'html': "COVER -> <h1 class=\"cover-header\">",
                'style': ".cover-header -> stencil-style, bold, rugged",
            },
            {
                'name': 'survival_footer',
                'content': "SURVIVALFOOTER: [a field manual footer]",
                'html': "SURVIVALFOOTER -> <p class=\"survival-footer\">",
                'style': ".survival-footer -> small text, centered, muted",
            },
        ],
    },
}


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


TWISTS = [
    "Every claim must be followed by a fake citation.",
    "A recurring character keeps interrupting the page.",
    "Written by someone who has never heard of the topic.",
    "The page is haunted and comments in the margins.",
    "Every third sentence is a dramatic non-sequitur.",
    "The author is being paid per word and it shows.",
    "All facts are technically true but deeply misleading.",
    "The page keeps trying to sell you something.",
    "Written in the style of a 3 AM group chat.",
    "The page is a government document that was never meant to be public.",
]
