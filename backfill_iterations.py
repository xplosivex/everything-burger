from app import create_app
from model import db, Page, PageIteration

app = create_app()

with app.app_context():
    pages = Page.query.filter_by(current_iteration_id=None).all()
    print(f"Found {len(pages)} pages without a root iteration.")

    for page in pages:
        root = PageIteration(
            page_id=page.id,
            parent_iteration_id=None,
            html_content=page.html_content,
            prompt=page.prompt,
            author_id=page.creator_id,
            iteration_number=0
        )
        db.session.add(root)
        db.session.flush()
        page.current_iteration_id = root.id

    db.session.commit()
    print(f"Backfilled {len(pages)} pages.")
