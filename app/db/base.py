"""SQLAlchemy declarative base. NFR-SEC-003: ORM only."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
