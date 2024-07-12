from app import app, db
import sqlalchemy as sa

with app.app_context():
    # Check if the 'role' column already exists
    inspector = sa.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('user')]
    
    if 'role' not in columns:
        with db.engine.connect() as connection:
            connection.execute(sa.text('ALTER TABLE user ADD COLUMN role VARCHAR(50) DEFAULT "user"'))
        print("Role column added to the user table.")
    else:
        print("The role column already exists in the user table.")
