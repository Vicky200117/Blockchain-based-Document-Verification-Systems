from app import app, db
from sqlalchemy import text

with app.app_context():
    # Add 'filename' column to 'document' table
    with db.engine.connect() as connection:
        connection.execute(text('ALTER TABLE document ADD COLUMN filename STRING'))

    db.session.commit()
