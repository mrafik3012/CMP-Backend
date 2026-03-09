from app.db.session import SessionLocal
from app.db.models.user import User
from datetime import datetime, timedelta

db = SessionLocal()
for email in ['pm@infraura.com', 'engineer@infraura.com', 'viewer@infraura.com']:
    u = db.query(User).filter(User.email == email).first()
    if u:
        u.trial_expires_at = datetime.utcnow() + timedelta(days=90)
        print(f'Fixed trial: {email}')
db.commit()
db.close()