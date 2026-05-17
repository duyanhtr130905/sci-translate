import os
import argparse
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


load_dotenv()

_TABLE_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_table_name(name: str) -> str:
    if not _TABLE_NAME_RE.match(name):
        raise ValueError(
            f"Tên bảng không hợp lệ: {name!r}. "
            "Chỉ cho phép ký tự [a-zA-Z_][a-zA-Z0-9_]*"
        )
    return name


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise EnvironmentError(
            "Biến môi trường DATABASE_URL chưa được set. "
            "Ví dụ: DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname"
        )
    return url


def get_engine():
    return create_engine(_get_database_url())


def check_connection():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).scalar()
            current_db = conn.execute(text("SELECT current_database();")).scalar()
            print("Kết nối PostgreSQL thành công.")
            print(f"Database: {current_db}")
            print(f"Version: {version}")
    except SQLAlchemyError as e:
        print("Kết nối PostgreSQL thất bại.")
        raise e


def ensure_table_exists(table_name: str = "translation_memory"):
    _validate_table_name(table_name)
    engine = get_engine()
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        en_text TEXT NOT NULL,
        vi_text TEXT NOT NULL
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))


def load_tsv(file_path: str, table_name: str = "translation_memory", if_exists: str = "append", has_header: bool = False):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    _validate_table_name(table_name)

    if has_header:
        df = pd.read_csv(file_path, sep="\t", encoding="utf-8")
        df = df.iloc[:, :2]
        df.columns = ["en_text", "vi_text"]
    else:
        df = pd.read_csv(
            file_path,
            sep="\t",
            header=None,
            names=["en_text", "vi_text"],
            encoding="utf-8"
        )

    # Làm sạch cơ bản
    df = df.dropna()
    df["en_text"] = df["en_text"].astype(str).str.strip()
    df["vi_text"] = df["vi_text"].astype(str).str.strip()
    df = df[(df["en_text"] != "") & (df["vi_text"] != "")]
    df = df.drop_duplicates()

    if df.empty:
        print("Không có dữ liệu hợp lệ để load.")
        return

    ensure_table_exists(table_name)

    engine = get_engine()

    if if_exists not in {"append", "replace", "fail"}:
        raise ValueError("if_exists chỉ nhận: append | replace | fail")

    if if_exists == "replace":
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name};"))
        ensure_table_exists(table_name)
        # dùng append phía dưới vì bảng đã được tạo lại
        write_mode = "append"
    else:
        write_mode = if_exists

    df.to_sql(
        name=table_name,
        con=engine,
        if_exists=write_mode,
        index=False,
        method="multi"
    )

    print(f"Đã load {len(df)} dòng vào bảng '{table_name}'.")


def preview_data(file_path: str, n: int = 5):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    df = pd.read_csv(
        file_path,
        sep="\t",
        header=None,
        names=["en_text", "vi_text"],
        encoding="utf-8"
    )

    print(df.head(n).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Load TSV song ngữ EN-VI vào PostgreSQL.")
    parser.add_argument("--file", help="Đường dẫn file TSV, ví dụ: corpus/train.tsv")
    parser.add_argument("--table", default="translation_memory", help="Tên bảng, mặc định: translation_memory")
    parser.add_argument(
        "--if-exists",
        default="append",
        choices=["append", "replace", "fail"],
        help="Cách ghi vào bảng nếu bảng đã tồn tại"
    )
    parser.add_argument("--check", action="store_true", help="Chỉ kiểm tra kết nối PostgreSQL")
    parser.add_argument("--has-header", action="store_true", help="File TSV có header row")
    parser.add_argument("--preview", action="store_true", help="Xem trước dữ liệu TSV")
    parser.add_argument("--rows", type=int, default=5, help="Số dòng preview, mặc định 5")

    args = parser.parse_args()

    if args.check:
        check_connection()
        return

    if not args.file:
        raise ValueError("Bạn phải truyền --file nếu không dùng --check")

    if args.preview:
        preview_data(args.file, args.rows)
        return

    load_tsv(args.file, args.table, args.if_exists, has_header=args.has_header)


if __name__ == "__main__":
    main()