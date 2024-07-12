from app import app, db

with app.app_context():
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    print("Tables in the database:")
    for table in tables:
        print(table)
