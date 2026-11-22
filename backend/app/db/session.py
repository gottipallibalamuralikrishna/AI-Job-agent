import os
import socket

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

database_url = make_url(settings.database_url)
on_vercel = os.getenv("VERCEL") == "1"
engine_options = {"connect_args": {}}
if "connect_timeout" not in database_url.query:
    engine_options["connect_args"]["connect_timeout"] = 5
if on_vercel:
    # Neon can pool connections at its endpoint. Don't retain sockets per function instance.
    engine_options["poolclass"] = NullPool
else:
    engine_options["pool_pre_ping"] = True

engine = create_engine(database_url, **engine_options)

if on_vercel and database_url.host and database_url.host.endswith(".neon.tech"):
    @event.listens_for(engine, "do_connect")
    def resolve_neon_ipv4(dialect, connection_record, args, params):
        if params.get("hostaddr"):
            return
        try:
            records = socket.getaddrinfo(
                database_url.host, database_url.port or 5432,
                socket.AF_INET, socket.SOCK_STREAM,
            )
        except socket.gaierror:
            return
        addresses = list(dict.fromkeys(record[4][0] for record in records))
        if addresses:
            # libpq requires a hostname entry for each address. Keep it for TLS SNI.
            params["host"] = ",".join([database_url.host] * len(addresses))
            params["hostaddr"] = ",".join(addresses)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
