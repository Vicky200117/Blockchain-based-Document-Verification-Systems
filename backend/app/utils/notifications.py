from app.models import Notification
from app import db

def create_notification(message):
    new_notification = Notification(message=message)
    db.session.add(new_notification)
    db.session.commit()
