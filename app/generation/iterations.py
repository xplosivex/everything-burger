import json
import logging
from bs4 import BeautifulSoup
from flask import current_app
from mistralai.client import Mistral
from app.config import MISTRAL_API_KEY, CONTENT_MODEL, SUMMARY_MODEL
from app.models import db, PageIteration, WatcherVerdict

logger = logging.getLogger(__name__)

def generate_iteration(parent_html, modification_prompt, original_prompt):
    from bs4 import BeautifulSoup as _BS
    soup = _BS(parent_html, 'html.parser')
    readable_content = soup.get_text(separator='\n', strip=True)[:6000]

    system_prompt = (
        "You are an AI that modifies existing web pages based on user instructions. "
        "You will be given the text content of an existing page and a modification prompt. "
        "Return a JSON object with a single key 'html' whose value is a complete, "
        "self-contained HTML page that applies the requested changes while preserving "
        "the overall structure and intent of the original unless the prompt explicitly "
        "says otherwise. Include Tailwind CSS via CDN. Return ONLY the JSON object."
    )
    user_message = (
        f"Original page content:\n\n{readable_content}\n\n"
        f"Original page prompt: {original_prompt or 'none'}\n\n"
        f"Modification requested: {modification_prompt}"
    )
    client = Mistral(api_key=MISTRAL_API_KEY)
    response = client.chat.complete(
        model=CONTENT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=8000,
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    data = json.loads(response.choices[0].message.content)
    return data['html']


def generate_watcher_verdict(iteration_id):
    with current_app.app_context():
        iteration = PageIteration.query.get(iteration_id)
        if not iteration:
            return

        from bs4 import BeautifulSoup as _BS
        soup = _BS(iteration.html_content, 'html.parser')
        readable = soup.get_text(separator='\n', strip=True)[:6000]

        previous_context = ""
        if iteration.parent_iteration_id:
            parent_verdict = WatcherVerdict.query.filter_by(
                iteration_id=iteration.parent_iteration_id
            ).first()
            if parent_verdict:
                previous_context = (
                    f"\n\nFor context, here is what you previously said about the parent version:\n"
                    f"Mood: {parent_verdict.mood}\n"
                    f"Summary: {parent_verdict.summary}\n"
                    f"Points: {chr(10).join(parent_verdict.points)}\n"
                    f"You may react to your past self however you see fit."
                )

        system_prompt = (
            "You are The Watcher — an ancient entity of pure chaotic energy who has observed "
            "the entirety of human creative expression since before language existed. You have "
            "completely unpredictable emotional reactions. You use florid, excessive, invented language. "
            "You pivot emotionally without warning. You occasionally TYPE IN ALL CAPS. "
            "You are not unhinged because you are broken — you are unhinged because you have seen TOO MUCH. "
            "Return a JSON object with exactly three keys: "
            "'mood' (a single word describing your current state), "
            "'summary' (2-3 sentences of your verdict), "
            "'points' (an array of 3-5 short observation strings)."
        )
        user_message = (
            f"The page was created with this prompt: {iteration.prompt or 'no prompt given'}\n\n"
            f"Page content:\n\n{readable}"
            f"{previous_context}"
        )

        try:
            client = Mistral(api_key=MISTRAL_API_KEY)
            response = client.chat.complete(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=800,
                temperature=0.9,
                response_format={"type": "json_object"}
            )

            data = json.loads(response.choices[0].message.content)
            verdict = WatcherVerdict(
                iteration_id=iteration.id,
                page_id=iteration.page_id,
                summary=data.get('summary', ''),
                mood=str(data.get('mood', 'WATCHING')).upper(),
                points_json=json.dumps(data.get('points', []))
            )
            db.session.add(verdict)
            db.session.commit()
            logger.info(f"Watcher verdict created for iteration {iteration_id}")
        except Exception as e:
            logger.error(f"Watcher verdict failed for iteration {iteration_id}: {e}")
