"""
Seed the database with a default admin account.
Run once: python seed.py
"""

from app import create_app
from app.extensions import db, bcrypt
from app.models import User

app = create_app()

with app.app_context():
    db.create_all()

    existing = User.query.filter_by(username="admin").first()
    if existing:
        print("Admin user already exists — skipping seed.")
    else:
        admin = User(
            username="admin",
            email="admin@tiktaktoe.local",
            password_hash=bcrypt.generate_password_hash("admin123").decode("utf-8"),
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()
        print("✅  Admin user created: admin / admin123")
        print("   ⚠️  Change this password before deploying to production!")
