from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Optional

from base_collector import BaseCollectorSpider


class ArxivCollectorSpider(BaseCollectorSpider):

    name = "arxiv_collector"
    allowed_domains = ["drive.google.com", "drive.usercontent.google.com"]

    custom_settings = {
        **BaseCollectorSpider.custom_settings,
        "DOWNLOAD_DELAY": 0.25,
        "AUTOTHROTTLE_START_DELAY": 0.25,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "RETRY_ENABLED": False,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "SCI-Translate/1.0 (arXiv sentence collector from Google Drive)"
        },
    }

    DEFAULT_EN_DRIVE_LINK = "https://drive.google.com/file/d/1iFGjupdZi61MtIohacJ2N68HfNpo_iHl/view?usp=sharing"
    DEFAULT_VI_DRIVE_LINK = "https://drive.google.com/file/d/1CIRG7V7N0Cpt3m34c61DGqdU4vx5zZ4R/view"

    def __init__(
        self,
        en_drive_link: str = DEFAULT_EN_DRIVE_LINK,
        vi_drive_link: str = DEFAULT_VI_DRIVE_LINK,
        output_mode: str = "pair",      # en | vi | pair
        max_results: Optional[str] = None,
        start_id: str = "1",
        keep_empty: str = "false",
        save_separate: str = "true",
        en_output_file: str = "raw/arxiv_sentences_en.json",
        vi_output_file: str = "raw/arxiv_sentences_vi.json",
        pair_output_file: Optional[str] = None,
        timeout: str = "60",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.en_drive_link = (en_drive_link or self.DEFAULT_EN_DRIVE_LINK).strip()
        self.vi_drive_link = (vi_drive_link or self.DEFAULT_VI_DRIVE_LINK).strip()
        self.output_mode = (output_mode or "pair").strip().lower()
        self.max_results = int(max_results) if max_results not in (None, "", "None") else None
        self.start_id = max(1, int(start_id))
        self.keep_empty = str(keep_empty).strip().lower() in {"1", "true", "yes", "y"}
        self.save_separate = str(save_separate).strip().lower() in {"1", "true", "yes", "y"}
        self.en_output_file = en_output_file
        self.vi_output_file = vi_output_file
        self.pair_output_file = pair_output_file
        self.timeout = max(5, int(timeout))

        self.total_emitted = 0
        self.total_pairs = 0

        if self.output_mode not in {"en", "vi", "pair"}:
            raise ValueError("output_mode phải là 'en', 'vi' hoặc 'pair'")

    # ---------- Scrapy entry ----------
    async def start(self):
        for record in self._run_collection():
            yield record

    def start_requests(self):
        yield from self._run_collection()

    # ---------- Main flow ----------
    def _run_collection(self):
        self.logger.info(
            "Bắt đầu đọc dữ liệu arXiv từ Google Drive | output_mode=%s | max_results=%s",
            self.output_mode,
            self.max_results,
        )

        en_sentences = self._load_drive_sentences(self.en_drive_link, lang="en")
        vi_sentences = self._load_drive_sentences(self.vi_drive_link, lang="vi")

        pairs = self._align_parallel_sentences(en_sentences, vi_sentences)
        self.total_pairs = len(pairs)

        self.logger.info(
            "Đã nạp EN=%s câu | VI=%s câu | aligned_pairs=%s",
            len(en_sentences),
            len(vi_sentences),
            len(pairs),
        )

        if self.save_separate:
            en_records = [{"id": row["id"], "sentence": row["en"]} for row in pairs]
            vi_records = [{"id": row["id"], "sentence": row["vi"]} for row in pairs]
            self.save_raw(en_records, output_file=self.en_output_file, format="json")
            self.save_raw(vi_records, output_file=self.vi_output_file, format="json")
            if self.pair_output_file:
                self.save_raw(pairs, output_file=self.pair_output_file, format="json")

        for row in pairs:
            if self.output_mode == "pair":
                self.total_emitted += 1
                yield row
            elif self.output_mode == "en":
                self.total_emitted += 1
                yield {"id": row["id"], "sentence": row["en"]}
            else:
                self.total_emitted += 1
                yield {"id": row["id"], "sentence": row["vi"]}

    # ---------- Drive download ----------
    @staticmethod
    def _extract_drive_file_id(url: str) -> str:
        patterns = [
            r"/file/d/([a-zA-Z0-9_-]+)",
            r"[?&]id=([a-zA-Z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError(f"Không trích xuất được file id từ link Google Drive: {url}")

    def _candidate_drive_urls(self, drive_link: str) -> list[str]:
        file_id = self._extract_drive_file_id(drive_link)
        return [
            f"https://drive.google.com/uc?export=download&id={file_id}",
            f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
        ]

    def _download_drive_bytes(self, drive_link: str) -> bytes:
        last_error: Exception | None = None
        for url in self._candidate_drive_urls(drive_link):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": self.custom_settings["DEFAULT_REQUEST_HEADERS"]["User-Agent"]},
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = resp.read()
                    if data:
                        return data
            except Exception as exc:
                last_error = exc
        raise RuntimeError(
            "Không tải được file Google Drive ở chế độ public. Hãy kiểm tra quyền chia sẻ 'Anyone with the link'."
        ) from last_error

    @staticmethod
    def _try_decode_bytes(data: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "utf-16", "utf-16-le", "utf-16-be"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    def _load_drive_sentences(self, drive_link: str, lang: str) -> list[str]:
        raw_bytes = self._download_drive_bytes(drive_link)
        text = self._try_decode_bytes(raw_bytes).strip()
        return self._parse_sentences_from_text(text, lang=lang)

    # ---------- Parsing ----------
    def _parse_sentences_from_text(self, text: str, lang: str) -> list[str]:
        # JSON
        try:
            obj = json.loads(text)
            sentences = self._extract_sentences_from_obj(obj, lang=lang)
            if sentences:
                return sentences
        except json.JSONDecodeError:
            pass

        # JSONL
        jsonl_sentences: list[str] = []
        jsonl_ok = True
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                jsonl_ok = False
                break
            jsonl_sentences.extend(self._extract_sentences_from_obj(obj, lang=lang))
        if jsonl_ok and jsonl_sentences:
            return jsonl_sentences

        # Plain text fallback: mỗi dòng là một câu
        plain_sentences: list[str] = []
        for line in text.splitlines():
            line = self.normalize_text(line)
            if not line:
                continue
            line = re.sub(r"^\s*\d+\s*(?:[\t,:;.-]\s*|\s+)", "", line)
            line = self.normalize_text(line)
            if line:
                plain_sentences.append(line)
        if plain_sentences:
            return plain_sentences

        raise ValueError("Không nhận diện được định dạng dữ liệu từ file Google Drive.")

    def _extract_sentences_from_obj(self, obj: Any, lang: str) -> list[str]:
        if isinstance(obj, list):
            return self._coerce_sentence_list(obj, lang=lang)

        if isinstance(obj, dict):
            # container keys phổ biến
            for key in ("data", "items", "rows", "records", "sentences", "translations"):
                value = obj.get(key)
                if isinstance(value, list):
                    sentences = self._coerce_sentence_list(value, lang=lang)
                    if sentences:
                        return sentences

            # record đơn
            return self._coerce_sentence_list([obj], lang=lang)

        return []

    def _coerce_sentence_list(self, items: Iterable[Any], lang: str) -> list[str]:
        sentences: list[str] = []
        for item in items:
            value = self._extract_sentence_value(item, lang=lang)
            value = self.normalize_text(value or "")
            if value:
                sentences.append(value)
        return sentences

    @staticmethod
    def _extract_sentence_value(item: Any, lang: str) -> str:
        if isinstance(item, str):
            return item

        if isinstance(item, dict):
            lang_keys = {
                "en": ("sentence", "en", "english", "source", "text", "content"),
                "vi": ("sentence", "vi", "vietnamese", "target", "text", "content"),
            }
            for key in lang_keys.get(lang, ("sentence", "text")):
                raw = item.get(key)
                if isinstance(raw, str) and raw.strip():
                    return raw

            translation = item.get("translation")
            if isinstance(translation, dict):
                for key in lang_keys.get(lang, (lang,)):
                    raw = translation.get(key)
                    if isinstance(raw, str) and raw.strip():
                        return raw

            raw = item.get(lang)
            if isinstance(raw, str) and raw.strip():
                return raw

        if item is None:
            return ""
        return str(item)

    # ---------- Alignment ----------
    def _align_parallel_sentences(self, en_sentences: list[str], vi_sentences: list[str]) -> list[dict[str, str]]:
        limit = min(len(en_sentences), len(vi_sentences))
        if self.max_results is not None:
            limit = min(limit, self.max_results)

        pairs: list[dict[str, str]] = []
        next_id = self.start_id
        for idx in range(limit):
            en = self.normalize_text(en_sentences[idx])
            vi = self.normalize_text(vi_sentences[idx])
            if not self.keep_empty and (not en or not vi):
                continue
            pairs.append({"id": next_id, "en": en, "vi": vi})
            next_id += 1
        return pairs

    def closed(self, reason):
        self.logger.info(
            "Hoàn tất arxiv_collector | output_mode=%s | emitted=%s | aligned_pairs=%s | reason=%s",
            self.output_mode,
            self.total_emitted,
            self.total_pairs,
            reason,
        )
