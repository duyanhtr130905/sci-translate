import os

from sqlalchemy import create_engine, text


def get_database_url() -> str:
    """
    Ưu tiên DATABASE_URL nếu đã set.
    Raise lỗi rõ ràng nếu chưa có.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise EnvironmentError(
            "Biến môi trường DATABASE_URL chưa được set. "
            "Ví dụ: DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname"
        )
    return url


def test_postgresql_connection_ok():
    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()

    assert result == 1