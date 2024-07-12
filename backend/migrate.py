from app import app, db, User, Document, Notification

with app.app_context():
    db.create_all()
    print("Database migration completed.")
