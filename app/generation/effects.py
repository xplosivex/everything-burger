import re
import math
from bs4 import BeautifulSoup
from app.generation.math import create_complex_calculation

def apply_effects(soup, active_effects, user_id):
    """Apply all active item effects to the generated HTML."""
    head = soup.find('head')
    if not head:
        head = soup.new_tag('head')
        html_tag = soup.find('html')
        if html_tag:
            html_tag.insert(0, head)

    for effect in active_effects:
        if effect.effect_type == 'green_glow':
            _apply_green_glow(soup, head)
        elif effect.effect_type == 'paragraph_colors':
            _apply_rainbow_paragraphs(soup)
        elif effect.effect_type == 'number_replacement':
            _apply_math_replacement(soup)
        elif effect.effect_type == 'font_size':
            _apply_font_effect(soup, head, font_size_multiplier=float(effect.effect_value))
        elif effect.effect_type == 'font_family':
            _apply_font_effect(soup, head, font_family=effect.effect_value)


def _apply_green_glow(soup, head):
    css = """<style>
        body * { text-shadow: 0 0 10px #00ff00, 0 0 20px #00ff00, 0 0 30px #00ff00 !important; }
        img { filter: drop-shadow(0 0 10px #00ff00) drop-shadow(0 0 20px #00ff00) !important; }
    </style>"""
    head.append(BeautifulSoup(css, 'html.parser'))


def _apply_rainbow_paragraphs(soup):
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD',
              '#D4A5A5', '#9B59B6', '#3498DB', '#E67E22', '#2ECC71']
    for i, p in enumerate(soup.find_all(['p', 'div'])):
        if p.name not in ('script', 'style'):
            color = colors[i % len(colors)]
            existing_style = p.get('style', '')
            p['style'] = f'color: {color}; {existing_style}'


def _apply_math_replacement(soup):
    for text_node in soup.find_all(string=True):
        if text_node.parent.name in ('script', 'style'):
            continue
        new_text = text_node
        for match in re.finditer(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', str(text_node)):
            num_str = match.group().replace(',', '')
            try:
                num = int(float(num_str))
                new_text = str(new_text).replace(match.group(), create_complex_calculation(num))
            except ValueError:
                continue
        text_node.replace_with(new_text)


def _apply_font_effect(soup, head, font_size_multiplier=None, font_family=None):
    rules = []
    if font_size_multiplier and font_size_multiplier != 1:
        rules.append(f'font-size: calc(1em * {font_size_multiplier}) !important')
        rules.append('line-height: 1.5 !important')
    if font_family:
        rules.append(f'font-family: {font_family}, cursive !important')
    if rules:
        css = f"<style>body * {{ {'; '.join(rules)} }}</style>"
        head.append(BeautifulSoup(css, 'html.parser'))


# ---------------------------------------------------------------------------
# STYLE INSTRUCTIONS (unchanged)
# ---------------------------------------------------------------------------

def _get_style_instructions(style: str) -> str | None:
    instructions = {
        'intellectual': (
            "Write everything in a hilariously pretentious, pseudo-intellectual style. "
            "Drop unnecessary philosophy references, use 'one might posit' and 'vis-a-vis' "
            "constantly, reference quantum mechanics to explain mundane things, and maintain "
            "smug superiority. The content blocks should still be short and varied -- just "
            "dripping with unearned intellectual confidence."
        ),
        'wizard': (
            "Write everything as an excitable wizard who can't contain their magical enthusiasm. "
            "Use 'By Merlin's beard!', reference spell components, describe ordinary things as "
            "enchantments, and treat the topic like ancient arcane knowledge. Keep blocks short "
            "and punchy -- wizards don't write essays, they cast verbal spells."
        ),
        'pirate': (
            "Write everything in full pirate speak. 'Ye' instead of 'you', nautical metaphors "
            "for everything, 'arr' and 'avast' liberally sprinkled. Treat every topic like it's "
            "treasure-related. Keep it punchy and fun -- pirates don't write dissertations, "
            "they scrawl on maps and yell things."
        ),
    }
    return instructions.get(style)
