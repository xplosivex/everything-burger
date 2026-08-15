# Content block definitions for the generation pipeline.
# Three tiers: STAPLE (generic, can repeat), COMMON (flavorful, once), EXOTIC (rare, once).

CORE_BLOCKS = {
    'title': {
        'prompt': 'TITLE: [funny, dramatic, or absurd page title]',
    },
    'subtitle': {
        'prompt': 'SUBTITLE: [punchy one-liner or tagline]',
    },
    'image': {
        'prompt': (
            'IMAGE: [3-5 word description for image search]\n'
            'CAPTION: [funny or descriptive caption]\n'
            '(include 1-3 images placed naturally throughout the page)'
        ),
    },
}


# ======================================================================
# STAPLE BLOCKS — high weight, allow duplicates
# ======================================================================

STAPLE_BLOCKS = {
    'paragraph': {
        'prompt': (
            'PARAGRAPH: [a short, punchy paragraph about the topic -- '
            '2-3 sentences max. Entertaining, opinionated, or funny. NOT an essay.]'
        ),
        'category': 'structure',
        'weight': 10,
    },
    'section': {
        'prompt': (
            'SECTION: [heading]\n'
            '[1-2 SHORT paragraphs, 2-3 sentences each. Punchy. Not an essay.]'
        ),
        'category': 'structure',
        'weight': 10,
    },
    'list': {
        'prompt': (
            'LIST: [title]\n'
            '- [item 1]\n- [item 2]\n- [item 3]\n- [item 4]\n'
            '(3-6 short items, can be bullet points, to-dos, or any simple list)'
        ),
        'category': 'structure',
        'weight': 8,
    },
    'numbered_list': {
        'prompt': (
            'NUMBEREDLIST: [title]\n'
            '1. [item]\n2. [item]\n3. [item]\n'
            '(3-6 items, ordered by importance, steps, or ranking)'
        ),
        'category': 'structure',
        'weight': 7,
    },
    'table': {
        'prompt': (
            'TABLE: [title]\n'
            '| [col1] | [col2] | [col3] |\n'
            '| [data] | [data] | [data] |\n'
            '| [data] | [data] | [data] |\n'
            '(2-4 columns, 2-5 rows -- can be funny comparisons, fake data, etc.)'
        ),
        'category': 'structure',
        'weight': 6,
    },
    'heading_text': {
        'prompt': (
            'HEADING: [bold, punchy heading -- a statement, question, or exclamation]\n'
            'TEXT: [1-2 sentences that follow up on the heading]'
        ),
        'category': 'structure',
        'weight': 8,
    },
    'callout_box': {
        'prompt': (
            'CALLOUT: [emoji or label like "NOTE", "TIP", "DID YOU KNOW"]\n'
            'CONTENT: [1-2 sentences of highlighted information or commentary]'
        ),
        'category': 'structure',
        'weight': 7,
    },
    'divider_text': {
        'prompt': 'DIVIDER: [a funny or thematic one-liner to break up the page, like a subheading or interstitial joke]',
        'category': 'structure',
        'weight': 5,
    },
    'bold_statement': {
        'prompt': 'BOLD: [one big, confident, standalone sentence -- displayed large and centered, like a pull quote]',
        'category': 'structure',
        'weight': 6,
    },
    'caption_block': {
        'prompt': (
            'CAPTIONBLOCK: [a short blurb that reads like a photo caption or museum placard, '
            '1-2 sentences, slightly formal but funny]'
        ),
        'category': 'structure',
        'weight': 4,
    },
    'summary_box': {
        'prompt': (
            'SUMMARY: [title like "TL;DR" or "The Bottom Line"]\n'
            'CONTENT: [2-3 sentence summary -- opinionated, funny, or deliberately unhelpful]'
        ),
        'category': 'structure',
        'weight': 5,
    },
    'key_value': {
        'prompt': (
            'KEYVALUE: [title]\n'
            'KEY: [label] -> VALUE: [data or funny answer]\n'
            'KEY: [label] -> VALUE: [data or funny answer]\n'
            'KEY: [label] -> VALUE: [data or funny answer]\n'
            '(3-5 key-value pairs, like a spec sheet or info card)'
        ),
        'category': 'structure',
        'weight': 5,
    },
    'blockquote': {
        'prompt': (
            'BLOCKQUOTE: [a notable, funny, or dramatic quote -- can be real-sounding or obviously fake]\n'
            'SOURCE: [attribution -- person, book, "ancient proverb", etc.]'
        ),
        'category': 'voice',
        'weight': 7,
    },
}

# ======================================================================
# COMMON BLOCKS — medium weight, no duplicates
# ======================================================================

COMMON_BLOCKS = {
    # --- VOICE & OPINION ---
    'funfact': {
        'prompt': 'FUNFACT: [one wild, surprising, or completely made-up "fact" -- stated with total confidence]',
        'category': 'voice',
        'weight': 6,
    },
    'quote': {
        'prompt': (
            'QUOTE: [absurd or hilariously specific quote]\n'
            'ATTRIBUTION: [funny fake source, e.g. "-- Dr. Gerald Hamsworth, Professor of Unnecessary Studies"]'
        ),
        'category': 'voice',
        'weight': 6,
    },
    'testimonial': {
        'prompt': (
            'TESTIMONIAL: [fake testimonial quote from a fake person]\n'
            'AUTHOR: [fake name and absurd title, e.g. "Brenda K., Certified Soup Whisperer"]'
        ),
        'category': 'voice',
        'weight': 5,
    },
    'debate': {
        'prompt': (
            'DEBATE: [hot take or controversial opinion stated as fact]\n'
            'COUNTERPOINT: [opposing view, equally confident]'
        ),
        'category': 'voice',
        'weight': 5,
    },
    'hot_take': {
        'prompt': 'HOTTAKE: [a single bold, provocative sentence about the topic that sounds like a viral tweet]',
        'category': 'voice',
        'weight': 6,
    },
    'unpopular_opinion': {
        'prompt': (
            'UNPOPULAROPINION: [an opinion about the topic framed as deeply controversial]\n'
            'DEFENSE: [1-2 sentence surprisingly compelling defense of it]'
        ),
        'category': 'voice',
        'weight': 4,
    },
    'overheard': {
        'prompt': (
            'OVERHEARD: [a snippet of fake conversation between two people about the topic, '
            '3-4 lines of dialogue, funny or absurd]'
        ),
        'category': 'voice',
        'weight': 4,
    },
    'review': {
        'prompt': (
            'REVIEW: [fake 1-5 star review of the topic as if it were a product or experience]\n'
            'STARS: [number 1-5]\n'
            'REVIEWER: [fake name and detail like "Verified Purchaser" or "Local Guide"]'
        ),
        'category': 'voice',
        'weight': 5,
    },
    'complaint': {
        'prompt': (
            'COMPLAINT: [fake angry customer complaint about the topic, '
            '2-3 sentences of escalating outrage]\n'
            'SIGNED: [fake name with petty title, e.g. "Karen M., Lifelong Taxpayer"]'
        ),
        'category': 'voice',
        'weight': 4,
    },
    'confession': {
        'prompt': (
            'CONFESSION: [a fake anonymous confession related to the topic, '
            'written like a late-night internet post -- funny or oddly specific]'
        ),
        'category': 'voice',
        'weight': 4,
    },
    'rant': {
        'prompt': (
            'RANT: [a 2-3 sentence passionate mini-rant about some aspect of the topic, '
            'getting increasingly unhinged by the last sentence]'
        ),
        'category': 'voice',
        'weight': 5,
    },
    'mic_drop': {
        'prompt': 'MICDROP: [one devastating, conversation-ending sentence about the topic -- stated with absolute finality]',
        'category': 'voice',
        'weight': 4,
    },

    # --- LISTS & RANKINGS ---
    'ranking': {
        'prompt': (
            'RANKING: [title of the ranking]\n'
            '1. [item] -- [one-line hot take]\n'
            '2. [item] -- [one-line hot take]\n'
            '3. [item] -- [one-line hot take]\n'
            '(3-7 items max)'
        ),
        'category': 'list',
        'weight': 6,
    },
    'tips': {
        'prompt': (
            'TIPS: [title]\n'
            '- [short tip 1]\n- [short tip 2]\n- [short tip 3]\n'
            '(3-5 tips, each one line)'
        ),
        'category': 'list',
        'weight': 6,
    },
    'stats': {
        'prompt': (
            'STATS: [title]\n'
            '- [made-up statistic with fake percentage]\n'
            '- [another fake stat]\n- [another fake stat]\n'
            '(2-4 stats)'
        ),
        'category': 'list',
        'weight': 5,
    },
    'tier_list': {
        'prompt': (
            'TIERLIST: [title -- what are we ranking?]\n'
            'S: [item]\nA: [item]\nB: [item]\nC: [item]\nF: [item]\n'
            '(one item per tier, with a 2-5 word justification each)'
        ),
        'category': 'list',
        'weight': 4,
    },
    'pros_cons': {
        'prompt': (
            'PROSCONS: [thing being evaluated]\n'
            'PRO: [genuine-sounding positive]\nPRO: [another]\n'
            'CON: [funny or absurd negative]\nCON: [another]\n'
            'VERDICT: [one-line final judgment]'
        ),
        'category': 'list',
        'weight': 5,
    },
    'checklist': {
        'prompt': (
            'CHECKLIST: [title -- a funny "are you ready" or "do you qualify" checklist]\n'
            '- [ ] [item 1]\n- [ ] [item 2]\n- [ ] [item 3]\n'
            '- [x] [item 4 -- pre-checked for comedic effect]\n'
            '(4-6 items)'
        ),
        'category': 'list',
        'weight': 4,
    },
    'starter_pack': {
        'prompt': (
            'STARTERPACK: [title -- "[Topic] Starter Pack"]\n'
            '- [item 1]\n- [item 2]\n- [item 3]\n- [item 4]\n- [item 5]\n'
            '(5-7 stereotypical items, funny and specific)'
        ),
        'category': 'list',
        'weight': 4,
    },
    'do_dont': {
        'prompt': (
            'DODONT: [title]\n'
            'DO: [good advice or funny instruction]\n'
            'DONT: [bad advice or absurd prohibition]\n'
            'DO: [another]\nDONT: [another]\n'
            '(2-4 pairs)'
        ),
        'category': 'list',
        'weight': 5,
    },
    'superlatives': {
        'prompt': (
            'SUPERLATIVES: [title -- "The [Topic] Awards"]\n'
            'MOST LIKELY TO: [item] -- [reason]\n'
            'BEST DRESSED: [item] -- [reason]\n'
            'LEAST LIKELY TO SURVIVE: [item] -- [reason]\n'
            '(3-5 funny superlative categories with winners)'
        ),
        'category': 'list',
        'weight': 4,
    },

    # --- DATA & COMPARISON ---
    'comparison': {
        'prompt': (
            'COMPARISON: [thing A] vs [thing B]\n'
            '[2-3 sentences comparing them in a funny or unexpected way]'
        ),
        'category': 'data',
        'weight': 5,
    },
    'timeline': {
        'prompt': (
            'TIMELINE: [title]\n'
            '- [year/date]: [event -- can be absurd]\n'
            '- [year/date]: [event]\n- [year/date]: [event]\n'
            '(3-5 entries)'
        ),
        'category': 'data',
        'weight': 5,
    },
    'poll': {
        'prompt': (
            'POLL: [funny poll question]\n'
            'OPTION: [answer 1]\nOPTION: [answer 2]\nOPTION: [answer 3]\n'
            '(2-4 options)'
        ),
        'category': 'data',
        'weight': 5,
    },
    'scale': {
        'prompt': (
            'SCALE: [what are we measuring? e.g. "How cursed is this?"]\n'
            '1: [label for low end]\n5: [label for middle]\n10: [label for high end]\n'
            'VERDICT: [where the topic lands, with a number and one-line reason]'
        ),
        'category': 'data',
        'weight': 4,
    },
    'matchup': {
        'prompt': (
            'MATCHUP: [thing A] vs [thing B] -- FIGHT!\n'
            'ROUND1: [category] -- Winner: [A or B] -- [why]\n'
            'ROUND2: [category] -- Winner: [A or B] -- [why]\n'
            'ROUND3: [category] -- Winner: [A or B] -- [why]\n'
            'CHAMPION: [winner and trash-talk victory line]'
        ),
        'category': 'data',
        'weight': 4,
    },
    'spectrum': {
        'prompt': (
            'SPECTRUM: [what dimension?]\n'
            'LEFT: [extreme 1]\nRIGHT: [extreme 2]\n'
            'ITEM: [thing] -- [where and why]\n'
            'ITEM: [thing] -- [where and why]\n'
            'ITEM: [thing] -- [where and why]\n'
            '(3-5 items placed on the spectrum)'
        ),
        'category': 'data',
        'weight': 3,
    },
    'flowchart': {
        'prompt': (
            'FLOWCHART: [title -- a decision tree or process]\n'
            'START: [question or starting point]\n'
            'IF YES: [outcome or next question]\n'
            'IF NO: [outcome or next question]\n'
            'RESULT: [funny final outcome]\n'
            '(a simple 3-5 step flowchart, can branch)'
        ),
        'category': 'data',
        'weight': 4,
    },
    'before_after': {
        'prompt': (
            'BEFOREAFTER: [title -- what changed?]\n'
            'BEFORE: [description of the "before" state, 1-2 sentences]\n'
            'AFTER: [description of the "after" state, 1-2 sentences]\n'
            'VERDICT: [was this an improvement? one-line take]'
        ),
        'category': 'data',
        'weight': 4,
    },
    'scoreboard': {
        'prompt': (
            'SCOREBOARD: [title -- what competition?]\n'
            '1ST: [item] -- [score or metric]\n'
            '2ND: [item] -- [score]\n'
            '3RD: [item] -- [score]\n'
            'LAST: [item] -- [score, hilariously low or absurd]'
        ),
        'category': 'data',
        'weight': 4,
    },

    # --- ALERTS & CALLOUTS ---
    'warning': {
        'prompt': 'WARNING: [fake warning box text -- dramatic, over-the-top, or weirdly specific]',
        'category': 'callout',
        'weight': 6,
    },
    'breaking': {
        'prompt': 'BREAKING: [fake breaking news headline -- dramatic and absurd]',
        'category': 'callout',
        'weight': 5,
    },
    'ad': {
        'prompt': 'AD: [fake advertisement for a ridiculous product or service related to the topic]',
        'category': 'callout',
        'weight': 5,
    },
    'sidebar': {
        'prompt': 'SIDEBAR: [interesting tangent, weird aside, or bonus fact]',
        'category': 'callout',
        'weight': 5,
    },
    'disclaimer': {
        'prompt': (
            'DISCLAIMER: [hilariously over-specific legal disclaimer related to the topic, '
            'written in fake legalese, 2-3 sentences]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'error_message': {
        'prompt': (
            'ERROR: [fake error message or 404 screen related to the topic, '
            'e.g. "ERROR 418: Too much sauce detected"]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'notification': {
        'prompt': (
            'NOTIFICATION: [fake phone/app notification related to the topic, '
            'e.g. "DUOLINGO: You forgot to practice [topic]. We know where you live."]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'news_ticker': {
        'prompt': (
            'TICKER: [3-4 fake scrolling news headlines related to the topic, '
            'separated by " | ", each one absurd and punchy]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'loading_screen': {
        'prompt': (
            'LOADING: [fake loading/progress message related to the topic, '
            'e.g. "Downloading more opinions... 67%%" or "Buffering hot takes..."]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'psa': {
        'prompt': (
            'PSA: [a fake public service announcement related to the topic, '
            'overly serious tone about something trivial, 2-3 sentences]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'update_banner': {
        'prompt': (
            'UPDATE: [a fake "EDIT" or "UPDATE" notice like you see on blog posts, '
            'e.g. "UPDATE (3:47 AM): We have been informed that [absurd correction]"]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'spoiler': {
        'prompt': (
            'SPOILER: [title -- what is being spoiled]\n'
            'CONTENT: [hidden content that is funny, anticlimactic, or absurd when revealed]'
        ),
        'category': 'callout',
        'weight': 4,
    },

    # --- INTERACTIVE ---
    'secret': {
        'prompt': (
            'SECRET: [title for expandable section, e.g. "Click to reveal the truth"]\n'
            'REVEAL: [hidden content -- funny, surprising, or anticlimactic]'
        ),
        'category': 'interactive',
        'weight': 5,
    },
    'quiz': {
        'prompt': (
            'QUIZ: [funny quiz question about the topic]\n'
            'A: [wrong answer]\nB: [wrong answer]\n'
            'C: [correct or funniest answer]\nD: [absurd answer]\n'
            'ANSWER: [letter and a snarky explanation]'
        ),
        'category': 'interactive',
        'weight': 5,
    },
    'fill_in_blank': {
        'prompt': (
            'FILLIN: [sentence with key words replaced by _____, mad-libs style]\n'
            'ANSWER: [intended words, plus a funnier alternative]'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'choose_adventure': {
        'prompt': (
            'ADVENTURE: [a mini choose-your-own-adventure scenario]\n'
            'OPTION_A: [choice and funny outcome in one sentence]\n'
            'OPTION_B: [choice and funny outcome]\n'
            'OPTION_C: [choice and funny outcome]'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'progress_bar': {
        'prompt': (
            'PROGRESS: [something being measured, e.g. "Progress toward enlightenment"]\n'
            'PERCENT: [a funny percentage, e.g. 47 or 103]\n'
            'NOTE: [one-line comment on the progress]'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'fake_comments': {
        'prompt': (
            'COMMENTS: [title, e.g. "What people are saying"]\n'
            'USER: [username] -- [comment, 1 sentence]\n'
            'USER: [username] -- [comment]\n'
            'USER: [username] -- [comment]\n'
            '(3-4 fake comments, increasingly unhinged)'
        ),
        'category': 'interactive',
        'weight': 5,
    },
    'fake_search': {
        'prompt': (
            'SEARCHBAR: [placeholder text for a fake search input]\n'
            'SUGGESTION: [autocomplete 1]\n'
            'SUGGESTION: [autocomplete 2]\n'
            'SUGGESTION: [autocomplete 3]'
        ),
        'category': 'interactive',
        'weight': 3,
    },
    'faq': {
        'prompt': (
            'FAQ: [title]\n'
            'Q: [funny question]\nA: [unhelpful or absurd answer]\n'
            'Q: [another]\nA: [another]\n'
            '(2-3 Q&A pairs)'
        ),
        'category': 'interactive',
        'weight': 5,
    },
    'recipe': {
        'prompt': (
            'RECIPE: [title -- a fake recipe for something that is NOT food, '
            'or food described absurdly]\n'
            'INGREDIENTS:\n- [item 1]\n- [item 2]\n- [item 3]\n'
            'STEPS:\n1. [step]\n2. [step]\n3. [step]\n'
            '(3-4 each, short and funny)'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'achievement': {
        'prompt': (
            'ACHIEVEMENT: [fake achievement/trophy unlocked notification]\n'
            'DESCRIPTION: [what the user "did" to earn it]'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'haiku': {
        'prompt': 'HAIKU: [a haiku (5-7-5 syllables) about the topic -- funny, weird, or deep]',
        'category': 'interactive',
        'weight': 4,
    },
    'marquee': {
        'prompt': 'MARQUEE: [scrolling text -- urgent, dramatic, or funny one-liner announcement]',
        'category': 'interactive',
        'weight': 3,
    },
    'this_or_that': {
        'prompt': (
            'THISORTHAT: [title]\n'
            'OPTION_A: [thing 1]\n'
            'OPTION_B: [thing 2]\n'
            '(presented as a "pick one" choice -- both options should be funny or hard to choose between)'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'rating_breakdown': {
        'prompt': (
            'RATINGBREAKDOWN: [what is being rated]\n'
            'TASTE: [score]/10 -- [one-line comment]\n'
            'VIBES: [score]/10 -- [comment]\n'
            'CHAOS: [score]/10 -- [comment]\n'
            'OVERALL: [score]/10\n'
            '(3-5 funny rating categories)'
        ),
        'category': 'interactive',
        'weight': 4,
    },
}


# ======================================================================
# EXOTIC BLOCKS — low weight, no duplicates, the "wow" factor
# ======================================================================

EXOTIC_BLOCKS = {
    'alignment_chart': {
        'prompt': (
            'ALIGNMENTCHART: [title -- what are we classifying?]\n'
            'LAWFUL GOOD: [item]\nNEUTRAL GOOD: [item]\nCHAOTIC GOOD: [item]\n'
            'LAWFUL NEUTRAL: [item]\nTRUE NEUTRAL: [item]\nCHAOTIC NEUTRAL: [item]\n'
            'LAWFUL EVIL: [item]\nNEUTRAL EVIL: [item]\nCHAOTIC EVIL: [item]'
        ),
        'category': 'data',
        'weight': 2,
    },
    'bingo': {
        'prompt': (
            'BINGO: [title -- e.g. "Things That Will Definitely Happen"]\n'
            '- [square 1]\n- [square 2]\n- [square 3]\n'
            '- [square 4]\n- [square 5]\n- [square 6]\n'
            '- [square 7]\n- [square 8]\n- [square 9]\n'
            '(exactly 9 items for a 3x3 bingo card)'
        ),
        'category': 'list',
        'weight': 2,
    },
    'classified': {
        'prompt': (
            'CLASSIFIED: [fake redacted government document about the topic, '
            'use [REDACTED] blocks for comedic effect, 2-3 sentences]'
        ),
        'category': 'callout',
        'weight': 2,
    },
    'prophecy': {
        'prompt': 'PROPHECY: [a dramatic, vaguely ominous prediction about the topic, written like an ancient oracle]',
        'category': 'voice',
        'weight': 2,
    },
    'wanted_poster': {
        'prompt': (
            'WANTED: [name or thing related to the topic]\n'
            'CRIME: [fake crime, dramatic and specific]\n'
            'REWARD: [absurd reward]\n'
            'DESCRIPTION: [1-2 sentence funny description]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'award': {
        'prompt': (
            'AWARD: [fake award name, very official-sounding]\n'
            'RECIPIENT: [who or what is receiving it]\n'
            'REASON: [ridiculous reason, 1-2 sentences]\n'
            'PRESENTED_BY: [fake organization with an absurd name]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'dictionary': {
        'prompt': (
            'DICTIONARY: [fake dictionary entry for a made-up word related to the topic]\n'
            'PRONUNCIATION: [fake phonetic spelling]\n'
            'DEFINITION: [funny definition, 1-2 sentences]\n'
            'USAGE: [example sentence using the word]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'field_guide': {
        'prompt': (
            'FIELDGUIDE: [treating something in the topic like a wildlife species]\n'
            'SPECIES: [fake Latin name]\n'
            'HABITAT: [where found]\n'
            'BEHAVIOR: [1-2 sentences nature-documentary style]\n'
            'DANGER_LEVEL: [rating with funny justification]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'dating_profile': {
        'prompt': (
            'DATINGPROFILE: [treating the topic like a person on a dating app]\n'
            'AGE: [funny answer]\n'
            'LOOKING_FOR: [what the topic "wants"]\n'
            'BIO: [2-3 sentence bio in the voice of the topic]\n'
            'DEALBREAKER: [one funny dealbreaker]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'horoscope': {
        'prompt': (
            'HOROSCOPE: [fake horoscope or fortune cookie prediction related to the topic, '
            '2-3 sentences, vague but dramatic]\n'
            'LUCKY_NUMBER: [a number with a funny reason]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'equation': {
        'prompt': (
            'EQUATION: [fake mathematical formula related to the topic, '
            'real-looking notation but nonsensical variables, '
            'e.g. "Fun = (Tacos x Friday) / Responsibility squared"]\n'
            'PROOF: [one-sentence fake proof or citation]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'transcript': {
        'prompt': (
            'TRANSCRIPT: [title -- fake transcript of what]\n'
            'SPEAKER1: [name] -- [line]\nSPEAKER2: [name] -- [line]\n'
            'SPEAKER1: [name] -- [line]\nSPEAKER2: [name] -- [line]\n'
            '(4-6 lines, escalating absurdity)'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'coupon': {
        'prompt': (
            'COUPON: [fake coupon related to the topic]\n'
            'DISCOUNT: [what you get]\n'
            'CODE: [funny promo code]\n'
            'EXPIRES: [absurd condition, e.g. "When the moon turns blue"]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'postcard': {
        'prompt': (
            'POSTCARD: [fake postcard message, 2-3 sentences "wish you were here" energy]\n'
            'FROM: [who sent it]\nTO: [who it\'s addressed to]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'footnote': {
        'prompt': (
            'FOOTNOTE: [fake academic footnote that starts reasonable and derails '
            'into something absurd or deeply personal, 2-3 sentences]'
        ),
        'category': 'voice',
        'weight': 2,
    },
    'obituary': {
        'prompt': (
            'OBITUARY: [a fake obituary for a concept, trend, or thing related to the topic]\n'
            'BORN: [when it started]\nDIED: [when/how it ended]\n'
            'SURVIVED_BY: [what it left behind]\n'
            'MEMORIAL: [how to honor its memory, funny]'
        ),
        'category': 'voice',
        'weight': 1,
    },
    'court_ruling': {
        'prompt': (
            'COURTRULING: [fake court case name, e.g. "The People vs. Pineapple Pizza"]\n'
            'CHARGE: [what the accused is charged with]\n'
            'VERDICT: [guilty/not guilty and the reasoning, 1-2 sentences]\n'
            'SENTENCE: [the punishment, absurd]'
        ),
        'category': 'voice',
        'weight': 1,
    },
    'autopsy_report': {
        'prompt': (
            'AUTOPSY: [fake autopsy/incident report for a failed project, trend, or idea related to the topic]\n'
            'CAUSE_OF_DEATH: [what went wrong]\n'
            'TIME_OF_DEATH: [when it died]\n'
            'CONTRIBUTING_FACTORS: [2-3 bullet points of funny reasons]\n'
            'EXAMINER_NOTES: [one-line snarky final observation]'
        ),
        'category': 'data',
        'weight': 1,
    },
    'text_message': {
        'prompt': (
            'TEXTCHAIN: [title -- who is texting who]\n'
            'MSG: [sender] > [short text message]\n'
            'MSG: [other] > [reply]\n'
            'MSG: [sender] > [reply]\n'
            'MSG: [other] > [reply]\n'
            '(4-6 messages, like a screenshot of a funny text exchange)'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'yelp_review': {
        'prompt': (
            'YELPREVIEW: [treating the topic like a restaurant or business]\n'
            'STARS: [1-5]\n'
            'REVIEW: [2-3 sentence fake Yelp review, passive-aggressive or weirdly specific]\n'
            'REVIEWER: [fake name]\n'
            'HELPFUL: [X out of Y people found this helpful -- funny numbers]'
        ),
        'category': 'voice',
        'weight': 2,
    },
    'weather_report': {
        'prompt': (
            'WEATHER: [fake weather forecast for the topic as if it were a location]\n'
            'TODAY: [condition and temperature, funny]\n'
            'TOMORROW: [forecast]\n'
            'WEEKEND: [forecast]\n'
            'ADVISORY: [fake weather advisory, dramatic]'
        ),
        'category': 'data',
        'weight': 1,
    },
    'resume': {
        'prompt': (
            'RESUME: [the topic presented as a job applicant\'s resume]\n'
            'OBJECTIVE: [what the topic "wants"]\n'
            'EXPERIENCE: [2-3 bullet points of fake work history]\n'
            'SKILLS: [3-4 fake skills]\n'
            'REFERENCES: [funny "available upon request" variant]'
        ),
        'category': 'interactive',
        'weight': 1,
    },
    'product_recall': {
        'prompt': (
            'RECALL: [fake product recall notice related to the topic]\n'
            'PRODUCT: [what is being recalled]\n'
            'REASON: [absurd safety concern]\n'
            'ACTION: [what consumers should do, funny]\n'
            'AFFECTED_UNITS: [ridiculous number]'
        ),
        'category': 'callout',
        'weight': 1,
    },
    'police_report': {
        'prompt': (
            'POLICEREPORT: [fake incident report related to the topic]\n'
            'INCIDENT: [what happened]\n'
            'SUSPECT: [description, funny]\n'
            'WITNESSES: [what witnesses said, contradictory or absurd]\n'
            'STATUS: [case status, e.g. "Under investigation by the Fun Police"]'
        ),
        'category': 'voice',
        'weight': 1,
    },
    'mad_lib': {
        'prompt': (
            'MADLIB: [a 3-4 sentence paragraph about the topic with 4-6 words replaced by '
            'their part of speech in brackets, e.g. "The [ADJECTIVE] [NOUN] decided to [VERB]..."]\n'
            'ANSWERS: [the intended funny answers for each blank]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'stock_ticker': {
        'prompt': (
            'STOCKTICKER: [treating aspects of the topic like stocks]\n'
            'SYMBOL: [3-4 letter ticker] -- [name] -- [price] -- [change with arrow up/down] -- [funny reason]\n'
            'SYMBOL: [ticker] -- [name] -- [price] -- [change] -- [reason]\n'
            'SYMBOL: [ticker] -- [name] -- [price] -- [change] -- [reason]\n'
            '(3-4 fake stock entries)'
        ),
        'category': 'data',
        'weight': 1,
    },
    'conspiracy': {
        'prompt': (
            'CONSPIRACY: [a fake conspiracy theory about the topic, '
            'written with escalating conviction and connecting random dots, '
            '3-4 sentences that start reasonable and end unhinged]'
        ),
        'category': 'voice',
        'weight': 2,
    },
    'survival_guide': {
        'prompt': (
            'SURVIVALGUIDE: [title -- "How to Survive [topic-related scenario]"]\n'
            'STEP1: [first thing to do]\n'
            'STEP2: [second thing]\n'
            'STEP3: [third thing, increasingly absurd]\n'
            'PROTIP: [one final piece of dubious wisdom]'
        ),
        'category': 'list',
        'weight': 2,
    },
    'infomercial': {
        'prompt': (
            'INFOMERCIAL: [fake infomercial script for a product related to the topic]\n'
            'PROBLEM: [dramatic description of a non-problem]\n'
            'SOLUTION: [the amazing product]\n'
            'BUTWAITSMORE: [bonus offer, increasingly ridiculous]\n'
            'CALLNOW: [fake phone number and urgency, e.g. "1-800-NOT-REAL -- operators are standing by!"]'
        ),
        'category': 'callout',
        'weight': 1,
    },
    'yearbook_superlative': {
        'prompt': (
            'YEARBOOK: [treating things in the topic like high school seniors]\n'
            'MOST_LIKELY_TO_SUCCEED: [item]\n'
            'CLASS_CLOWN: [item]\n'
            'BEST_HAIR: [item]\n'
            'MOST_CHANGED: [item]\n'
            'BEST_COUPLE: [item A] & [item B]\n'
            '(5-7 superlatives, each one line)'
        ),
        'category': 'list',
        'weight': 1,
    },
    'loading_bar_story': {
        'prompt': (
            'LOADINGSTORY: [a progress bar that tells a story as it loads]\n'
            '10%%: [status message]\n'
            '35%%: [status, things getting weird]\n'
            '67%%: [status, something has gone wrong]\n'
            '89%%: [status, existential crisis]\n'
            '100%%: [final status, anticlimax or punchline]'
        ),
        'category': 'interactive',
        'weight': 1,
    },
    'complaint_form': {
        'prompt': (
            'COMPLAINTFORM: [title -- fake official complaint form]\n'
            'FIELD: Name: [pre-filled funny name]\n'
            'FIELD: Nature of complaint: [pre-filled absurd complaint]\n'
            'FIELD: Desired resolution: [unreasonable demand]\n'
            'FIELD: How angry are you (1-10): [number higher than 10]\n'
            'OFFICE_USE_ONLY: [snarky internal note]'
        ),
        'category': 'interactive',
        'weight': 1,
    },
    'wikipedia_vandalism': {
        'prompt': (
            'WIKIVANDAL: [a fake Wikipedia-style paragraph about the topic that has been '
            '"vandalized" with obviously wrong edits in brackets, '
            'e.g. "The Eiffel Tower, located in [Gary, Indiana], was built in [1997] by [my uncle Steve]..."]'
        ),
        'category': 'voice',
        'weight': 1,
    },
    'email_chain': {
        'prompt': (
            'EMAILCHAIN: [subject line]\n'
            'FROM: [sender] -- [1-2 sentence email about the topic]\n'
            'RE: [responder] -- [reply]\n'
            'RE:RE: [original sender] -- [reply that escalates]\n'
            'RE:RE:RE: [responder] -- [final reply, passive-aggressive or unhinged]\n'
            '(like a screenshot of a corporate email thread gone wrong)'
        ),
        'category': 'interactive',
        'weight': 1,
    },
    'instruction_manual': {
        'prompt': (
            'MANUAL: [title -- fake instruction manual for something related to the topic]\n'
            'STEP1: [instruction with unnecessary warning]\n'
            'STEP2: [instruction that assumes too much]\n'
            'STEP3: [instruction that contradicts step 1]\n'
            'TROUBLESHOOTING: [one FAQ-style troubleshoot that is deeply unhelpful]\n'
            'WARRANTY: [absurd warranty terms]'
        ),
        'category': 'interactive',
        'weight': 1,
    },
}

# Category labels for balanced selection
BLOCK_CATEGORIES = ['structure', 'voice', 'list', 'data', 'callout', 'interactive']
