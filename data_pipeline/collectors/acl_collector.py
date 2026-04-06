import json
import re
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

from base_collector import BaseCollectorSpider


class ACLCollectorSpider(BaseCollectorSpider):

    name = "acl_collector"
    allowed_domains = [
        "drive.google.com",
        "drive.usercontent.google.com",
        "docs.google.com",
    ]

    custom_settings = {
        **BaseCollectorSpider.custom_settings,
        "DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": False,
        "AUTOTHROTTLE_START_DELAY": 0.2,
        "AUTOTHROTTLE_MAX_DELAY": 3.0,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [403, 429, 500, 502, 503, 504],
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "SCI-Translate/1.0 (ACL Drive collector)"
        },
    }

    def __init__(
        self,
        en_drive_link="https://drive.google.com/file/d/1GxJ9b5hvcIwAEu3OfwpRwlX_5VpakJ4O/view",
        vi_drive_link="https://drive.google.com/file/d/1WEH61JwcRGakx54-SM1NbMtc4h_pg7v0/view",
        max_results=None,
        output_mode="en",  # en | vi
        save_separate="true",
        en_output_file="raw/acl_sentences_en.json",
        vi_output_file="raw/acl_sentences_vi.json",
        start_id="1",
        keep_empty="false",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.en_drive_link = (en_drive_link or "").strip()
        self.vi_drive_link = (vi_drive_link or "").strip()
        self.max_results = int(max_results) if max_results not in (None, "", "None") else None
        self.output_mode = (output_mode or "en").strip().lower()
        self.save_separate = str(save_separate).strip().lower() in {"1", "true", "yes", "y"}
        self.en_output_file = en_output_file or "raw/acl_sentences_en.json"
        self.vi_output_file = vi_output_file or "raw/acl_sentences_vi.json"
        self.start_id = int(start_id)
        self.keep_empty = str(keep_empty).strip().lower() in {"1", "true", "yes", "y"}

        if self.output_mode not in {"en", "vi"}:
            raise ValueError("output_mode phải là 'en' hoặc 'vi'")

        if not self.en_drive_link:
            raise ValueError("Thiếu en_drive_link")
        if not self.vi_drive_link:
            raise ValueError("Thiếu vi_drive_link")

        self.en_sentences: list[str] = []
        self.vi_sentences: list[str] = []
        self.saved_outputs = False

    @staticmethod
    def extract_drive_file_id(url: str) -> str:
        patterns = [
            r"/file/d/([a-zA-Z0-9_-]+)",
            r"[?&]id=([a-zA-Z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        parsed = urlparse(url)
        query_id = parse_qs(parsed.query).get("id")
        if query_id:
            return query_id[0]

        raise ValueError(f"Không trích xuất được file id từ link Google Drive: {url}")

    @classmethod
    def build_drive_download_urls(cls, public_link: str) -> list[str]:
        file_id = cls.extract_drive_file_id(public_link)
        return [
            f"https://drive.google.com/uc?export=download&id={file_id}",
            f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
        ]

    @staticmethod
    def _decode_bytes(data: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "utf-16", "utf-16-le", "utf-16-be"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    def _coerce_sentence_records(self, items: Iterable[Any]) -> list[str]:
        sentences: list[str] = []
        for item in items:
            value: str | None = None

            if isinstance(item, str):
                value = item
            elif isinstance(item, dict):
                for key in ("sentence", "text", "content", "en", "vi", "translation", "target"):
                    raw = item.get(key)
                    if isinstance(raw, str) and raw.strip():
                        value = raw
                        break
            elif item is not None:
                value = str(item)

            value = self.normalize_text(value or "")
            if value or self.keep_empty:
                sentences.append(value)
        return sentences

    def _extract_sentences_from_obj(self, obj: Any) -> list[str]:
        if isinstance(obj, list):
            return self._coerce_sentence_records(obj)

        if isinstance(obj, dict):
            for key in ("data", "items", "sentences", "rows", "records", "translations"):
                value = obj.get(key)
                if isinstance(value, list):
                    return self._coerce_sentence_records(value)

            maybe_one = self._coerce_sentence_records([obj])
            if maybe_one:
                return maybe_one

        return []

    def parse_drive_payload(self, body: bytes) -> list[str]:
        text = self._decode_bytes(body)
        stripped = text.strip()
        if not stripped:
            return []

        try:
            obj = json.loads(stripped)
            sentences = self._extract_sentences_from_obj(obj)
            if sentences:
                return self._filter_empty(sentences)
        except json.JSONDecodeError:
            pass

        jsonl_sentences: list[str] = []
        jsonl_ok = True
        for line in stripped.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                jsonl_ok = False
                break
            jsonl_sentences.extend(self._extract_sentences_from_obj(obj))
        if jsonl_ok and jsonl_sentences:
            return self._filter_empty(jsonl_sentences)

        text_sentences: list[str] = []
        for line in stripped.splitlines():
            line = self.normalize_text(line)
            if not line and not self.keep_empty:
                continue
            line = re.sub(r"^\s*\d+\s*(?:[\t,:;.-]\s*|\s+)", "", line)
            line = self.normalize_text(line)
            if line or self.keep_empty:
                text_sentences.append(line)

        return self._filter_empty(text_sentences)

    def _filter_empty(self, sentences: list[str]) -> list[str]:
        if self.keep_empty:
            return sentences
        return [s for s in sentences if s]

    def build_sentence_records(self, sentences: list[str]) -> list[dict[str, Any]]:
        limited = sentences[: self.max_results] if self.max_results is not None else sentences
        return [
            {"id": self.start_id + idx, "sentence": sentence}
            for idx, sentence in enumerate(limited)
        ]

    def start_requests(self):
        urls = self.build_drive_download_urls(self.en_drive_link)
        yield self.fetch(
            url=urls[0],
            callback=self.parse_drive_file,
            cb_kwargs={"kind": "en", "fallback_urls": urls, "url_index": 0},
        )

    async def start(self):
        urls = self.build_drive_download_urls(self.en_drive_link)
        yield self.fetch(
            url=urls[0],
            callback=self.parse_drive_file,
            cb_kwargs={"kind": "en", "fallback_urls": urls, "url_index": 0},
        )

    def _retry_next_url(self, fallback_urls: list[str], url_index: int, kind: str):
        next_index = url_index + 1
        if next_index < len(fallback_urls):
            self.logger.warning("Thử lại nguồn %s với URL fallback #%s", kind, next_index + 1)
            return self.fetch(
                url=fallback_urls[next_index],
                callback=self.parse_drive_file,
                cb_kwargs={"kind": kind, "fallback_urls": fallback_urls, "url_index": next_index},
            )
        return None

    def parse_drive_file(self, response, kind: str, fallback_urls: list[str], url_index: int = 0):
        if response.status != 200:
            self.logger.warning("Không tải được file %s | HTTP %s | %s", kind, response.status, response.url)
            retry_req = self._retry_next_url(fallback_urls, url_index, kind)
            if retry_req is not None:
                yield retry_req
            return

        try:
            sentences = self.parse_drive_payload(response.body)
        except Exception as exc:
            self.logger.warning("Không parse được file %s từ %s: %s", kind, response.url, exc)
            retry_req = self._retry_next_url(fallback_urls, url_index, kind)
            if retry_req is not None:
                yield retry_req
            return

        if not sentences:
            self.logger.warning("File %s không có câu hợp lệ: %s", kind, response.url)
            retry_req = self._retry_next_url(fallback_urls, url_index, kind)
            if retry_req is not None:
                yield retry_req
            return

        if kind == "en":
            self.en_sentences = sentences
            self.logger.info("Đã load EN: %s câu", len(self.en_sentences))
            vi_urls = self.build_drive_download_urls(self.vi_drive_link)
            yield self.fetch(
                url=vi_urls[0],
                callback=self.parse_drive_file,
                cb_kwargs={"kind": "vi", "fallback_urls": vi_urls, "url_index": 0},
            )
            return

        self.vi_sentences = sentences
        self.logger.info("Đã load VI: %s câu", len(self.vi_sentences))

        if self.save_separate and not self.saved_outputs:
            en_records = self.build_sentence_records(self.en_sentences)
            vi_records = self.build_sentence_records(self.vi_sentences)
            self.save_raw(en_records, self.en_output_file, format="json")
            self.save_raw(vi_records, self.vi_output_file, format="json")
            self.saved_outputs = True
            self.logger.info(
                "Đã lưu file riêng | en=%s | vi=%s",
                self.en_output_file,
                self.vi_output_file,
            )

        for item in self.iter_output_items():
            yield item

    def iter_output_items(self):
        if self.output_mode == "vi":
            yield from self.build_sentence_records(self.vi_sentences)
            return

        yield from self.build_sentence_records(self.en_sentences)
