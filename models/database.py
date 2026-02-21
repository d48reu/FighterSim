"""Database engine and session factory for MMA Management Simulator."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_db_engine(db_url: str):
    return create_engine(db_url, echo=False)


def create_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)
