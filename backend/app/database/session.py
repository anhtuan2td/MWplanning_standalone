from collections.abc import Generator
import time

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.site import Base


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(retries: int = 20, delay_seconds: float = 1.5) -> None:
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            _ensure_site_columns()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(delay_seconds)
    if last_error:
        raise last_error


def _ensure_site_columns() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("sites"):
        return
    columns = {column["name"] for column in inspector.get_columns("sites")}
    statements = []
    if "overload" not in columns:
        statements.append("ALTER TABLE sites ADD COLUMN overload INTEGER DEFAULT 0")
    if "diverse_routing" not in columns:
        statements.append("ALTER TABLE sites ADD COLUMN diverse_routing BOOLEAN DEFAULT FALSE")
    if "cells_4g" not in columns:
        statements.append("ALTER TABLE sites ADD COLUMN cells_4g INTEGER")
    if "cells_5g" not in columns:
        statements.append("ALTER TABLE sites ADD COLUMN cells_5g INTEGER")
    should_migrate_overload = "overload" in columns and engine.dialect.name == "postgresql"
    if not statements and not should_migrate_overload:
        return
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
        if should_migrate_overload:
            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_name = 'sites'
                              AND column_name = 'overload'
                              AND data_type = 'boolean'
                        ) THEN
                            ALTER TABLE sites ALTER COLUMN overload DROP DEFAULT;
                            ALTER TABLE sites
                            ALTER COLUMN overload TYPE INTEGER
                            USING CASE WHEN overload THEN 1 ELSE 0 END;
                            ALTER TABLE sites ALTER COLUMN overload SET DEFAULT 0;
                        END IF;
                    END $$;
                    """
                )
            )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
