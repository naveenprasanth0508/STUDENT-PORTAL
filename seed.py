"""Creates two demo users + one request. Passwords come from the environment (never hardcoded)."""
import os
from app.db import Base, SessionLocal, engine
from app.deps import hash_pw
from app.models import Request, Timeline, User

Base.metadata.create_all(engine)
with SessionLocal() as db:
    if db.query(User).first():
        raise SystemExit("Already seeded.")
    admin = User(name="Admin Alice", email="admin@example.com", role="admin", password_hash=hash_pw(os.environ["SEED_ADMIN_PASSWORD"]))
    stu = User(name="Sam Student", email="student@example.com", role="student", password_hash=hash_pw(os.environ["SEED_STUDENT_PASSWORD"]))
    db.add_all([admin, stu]); db.flush()
    r = Request(subject="Transcript request", category="Certificate", priority="Medium", status="Pending", archived=False,
                description="Sample request created by seed.py for testing.", student_id=stu.id)
    r.timeline.append(Timeline(status="Pending", by=stu.name))
    db.add(r); db.commit()
    print("Seeded admin@example.com and student@example.com")
