from app.db.session import SessionLocal
from app.db.models.user import User
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')
new_hash = pwd_ctx.hash('Test@1234')

db = SessionLocal()
for email in ['pm@infraura.com', 'engineer@infraura.com', 'viewer@infraura.com']:
    u = db.query(User).filter(User.email == email).first()
    if u:
        u.password_hash = new_hash
        print(f'Reset: {email}')
db.commit()
db.close()
print('Done')