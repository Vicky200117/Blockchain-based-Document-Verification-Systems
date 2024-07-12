import os
import shutil
from app import db, create_app
from app.models import Document

# Create the app instance
app = create_app()

# Clear the Document table
with app.app_context():
    db.session.query(Document).delete()
    db.session.commit()
    print("All documents have been cleared from the database.")

# Clear the uploads directory
upload_folder = 'uploads'

if os.path.exists(upload_folder):
    shutil.rmtree(upload_folder)
    os.makedirs(upload_folder)
    print("All files have been cleared from the uploads directory.")
