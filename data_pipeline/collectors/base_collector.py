from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Iterable

import scrapy


class BaseCollectorSpider(scrapy.Spider):

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 30.0,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 2,
        "FEED_EXPORT_ENCODING": "utf-8",
        "LOG_LEVEL": "INFO",
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "SCI-Translate/1.0 (base collector)",
        },
    }

    ABBREVIATIONS = {
        "e.g.",
        "i.e.",
        "etc.",
        "vs.",
        "mr.",
        "mrs.",
        "ms.",
        "dr.",
        "prof.",
        "fig.",
        "eq.",
        "al.",
        "et al.",
    }

    WS_RE = re.compile(r"\s+")
    SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(\[])")

    @classmethod
    def fetch(cls, url: str, callback=None, cb_kwargs: dict[str, Any] | None = None, **kwargs):
        """Wrapper tạo Scrapy Request để các collector dùng cùng một kiểu gọi."""
        return scrapy.Request(url=url, callback=callback, cb_kwargs=cb_kwargs or {}, dont_filter=True, **kwargs)

    @classmethod
    def normalize_text(cls, text: str | None) -> str:
        """Chuẩn hóa text: decode HTML, bỏ NBSP, gom khoảng trắng."""
        text = html.unescape(text or "")
        text = text.replace("\u00a0", " ")
        return cls.WS_RE.sub(" ", text).strip()

    @classmethod
    def protect_abbreviations(cls, text: str) -> str:
        protected = text
        for abbr in sorted(cls.ABBREVIATIONS, key=len, reverse=True):
            token = abbr.replace(".", "<DOT>")
            protected = re.sub(re.escape(abbr), token, protected, flags=re.IGNORECASE)
        protected = re.sub(r"(?<=\d)\.(?=\d)", "<DOT>", protected)
        return protected

    @staticmethod
    def restore_abbreviations(text: str) -> str:
        return text.replace("<DOT>", ".")

    @classmethod
    def smart_split_sentences(cls, text: str, min_words: int = 3) -> list[str]:
        """
        Tách câu nhưng tránh tách sai ở:
        - e.g. / i.e. / etc.
        - số thập phân như 3.8
        """
        text = cls.normalize_text(text)
        if not text:
            return []

        protected = cls.protect_abbreviations(text)
        raw_parts = cls.SENTENCE_END_RE.split(protected)

        sentences: list[str] = []
        for part in raw_parts:
            sentence = cls.restore_abbreviations(part).strip()
            if not sentence:
                continue
            if len(sentence.split()) < min_words:
                continue
            sentences.append(sentence)
        return sentences

    @classmethod
    def match_query(cls, text: str, query: str | None) -> bool:
        """
        Kiểm tra text có chứa tất cả token quan trọng trong query không.
        Dùng cho filter nhẹ, không nhằm thay thế search engine.
        """
        if not query:
            return True

        text_norm = cls.normalize_text(text).lower()
        query_norm = cls.normalize_text(query).lower()
        if not query_norm:
            return True

        tokens = [
            tok for tok in re.split(r"\s+|\bAND\b|\bOR\b|[:()\[\]{}\"']+", query_norm)
            if tok and tok not in {"and", "or", "all", "cat"}
        ]
        if not tokens:
            return True
        return all(tok in text_norm for tok in tokens)

    @staticmethod
    def _ensure_parent_dir(output_file: str | Path) -> Path:
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def save_raw(
        cls,
        data: Iterable[Any],
        output_file: str | Path,
        format: str = "json",
        encoding: str = "utf-8",
    ) -> Path:
        """
        Lưu dữ liệu ra file.

        Supported formats:
        - json  : toàn bộ list thành 1 mảng JSON
        - jsonl : mỗi record 1 dòng JSON
        - txt   : mỗi record 1 dòng text
        """
        path = cls._ensure_parent_dir(output_file)
        fmt = (format or "json").strip().lower()
        items = list(data)

        if fmt == "json":
            path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding=encoding)
        elif fmt == "jsonl":
            with path.open("w", encoding=encoding, newline="\n") as f:
                for item in items:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
        elif fmt == "txt":
            with path.open("w", encoding=encoding, newline="\n") as f:
                for item in items:
                    if isinstance(item, dict):
                        if "sentence" in item:
                            line = str(item["sentence"])
                        elif "text" in item:
                            line = str(item["text"])
                        else:
                            line = json.dumps(item, ensure_ascii=False)
                    else:
                        line = str(item)
                    f.write(cls.normalize_text(line) + "\n")
        else:
            raise ValueError("format phải là 'json', 'jsonl' hoặc 'txt'")

        return path
