"""
Ollama Translation Engine
Sử dụng Ollama LLM cục bộ để dịch văn bản khoa học EN→VI.
Kết hợp RAG context và KG terms vào prompt để tăng chất lượng dịch.
"""

import os
import logging
from typing import Optional

import ollama as ollama_sdk
from models.ollama_config import OllamaConfig

logger = logging.getLogger(__name__)


class OllamaEngine:
    """Translation engine sử dụng Ollama LLM cục bộ."""

    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig.from_env()
        self.client = ollama_sdk.Client(host=self.config.base_url)
        logger.info(
            f"OllamaEngine initialized: model={self.config.model}, "
            f"url={self.config.base_url}"
        )

    def health_check(self) -> dict:
        """Kiểm tra Ollama daemon và model đã sẵn sàng chưa."""
        try:
            models = self.client.list()
            model_names = [m.model for m in models.models]
            available = self.config.model in model_names or any(
                self.config.model in name for name in model_names
            )
            return {
                "status": "ok" if available else "model_not_found",
                "engine": "ollama",
                "model": self.config.model,
                "ollama_url": self.config.base_url,
                "available_models": model_names,
            }
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return {
                "status": "error",
                "engine": "ollama",
                "error": str(e),
            }

    def translate(
        self,
        text: str,
        domain: str = "general",
        rag_context: Optional[str] = None,
        kg_terms: Optional[dict] = None,
    ) -> str:
        """
        Dịch văn bản EN→VI sử dụng Ollama LLM.

        Args:
            text: Câu/đoạn văn bản tiếng Anh cần dịch.
            domain: Lĩnh vực khoa học (computer_science, biology, physics, ...).
            rag_context: Context tương tự từ RAG pipeline (nếu có).
            kg_terms: Dict thuật ngữ chuyên ngành {EN: VI} từ Knowledge Graph.

        Returns:
            Bản dịch tiếng Việt.
        """
        system_prompt = self._build_system_prompt(domain)
        user_prompt = self._build_user_prompt(text, rag_context, kg_terms)

        try:
            response = self.client.chat(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={
                    "temperature": self.config.temperature,
                    "num_ctx": self.config.num_ctx,
                },
            )
            translated = response.message.content.strip()
            logger.debug(f"Translated: '{text[:50]}...' → '{translated[:50]}...'")
            return translated

        except Exception as e:
            logger.error(f"Ollama translation failed: {e}")
            raise RuntimeError(f"Translation failed: {e}") from e

    def _build_system_prompt(self, domain: str) -> str:
        """Tạo system prompt cho LLM dựa trên domain."""
        domain_map = {
            "computer_science": "khoa học máy tính",
            "biology": "sinh học",
            "physics": "vật lý",
            "chemistry": "hoá học",
            "general": "tổng quát",
        }
        domain_vi = domain_map.get(domain, "tổng quát")

        return (
            f"Bạn là chuyên gia dịch thuật tài liệu khoa học lĩnh vực {domain_vi} "
            f"từ tiếng Anh sang tiếng Việt.\n\n"
            f"Quy tắc:\n"
            f"1. Dịch chính xác, giữ nguyên ý nghĩa khoa học.\n"
            f"2. Sử dụng đúng thuật ngữ chuyên ngành tiếng Việt (nếu được cung cấp).\n"
            f"3. Giữ nguyên các ký hiệu toán học, công thức, tên riêng.\n"
            f"4. CHỈ trả về bản dịch, không giải thích thêm.\n"
            f"5. Giữ format đoạn văn giống bản gốc."
        )

    def _build_user_prompt(
        self,
        text: str,
        rag_context: Optional[str] = None,
        kg_terms: Optional[dict] = None,
    ) -> str:
        """Tạo user prompt kết hợp RAG context và KG terms."""
        parts = []

        if rag_context:
            parts.append(
                f"Tham khảo các bản dịch tương tự:\n{rag_context}\n"
            )

        if kg_terms:
            terms_str = "\n".join(
                f"  - {en} → {vi}" for en, vi in kg_terms.items()
            )
            parts.append(
                f"Thuật ngữ chuyên ngành cần sử dụng:\n{terms_str}\n"
            )

        parts.append(f"Dịch đoạn sau sang tiếng Việt:\n{text}")

        return "\n".join(parts)
