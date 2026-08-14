import time
from app import create_app, generate_watcher_verdict
from model import db, PageIteration, WatcherVerdict

app = create_app()

with app.app_context():
    pending = db.session.query(PageIteration).outerjoin(
        WatcherVerdict, WatcherVerdict.iteration_id == PageIteration.id
    ).filter(
        PageIteration.parent_iteration_id == None,
        WatcherVerdict.id == None
    ).all()

    print(f"Found {len(pending)} iterations without a verdict.")

    for i, iteration in enumerate(pending):
        try:
            generate_watcher_verdict(iteration.id)
            print(f"[{i + 1}/{len(pending)}] Verdict generated for iteration {iteration.id} (page {iteration.page_id})")
        except Exception as e:
            print(f"[{i + 1}/{len(pending)}] FAILED for iteration {iteration.id}: {e}")
        time.sleep(1)

    print("Backfill complete.")
