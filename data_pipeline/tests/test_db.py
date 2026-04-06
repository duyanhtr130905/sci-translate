import os

from sqlalchemy import create_engine, text


def get_database_url() -> str:
    """
    Ưu tiên DATABASE_URL nếu đã set.
    Nếu chưa có thì dùng mặc định để test từ máy host.
    """
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/sci_translate",
    )


def test_postgresql_connection_ok():
    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()

    assert result == 1