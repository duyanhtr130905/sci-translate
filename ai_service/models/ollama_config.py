"""
Ollama Configuration
Cấu hình kết nối và tham số cho Ollama LLM.
"""

import os
from dataclasses import dataclass, field


@dataclass
class OllamaConfig:
    """Configuration cho Ollama translation engine."""

    # Ollama server
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"

    # Generation parameters
    temperature: float = 0.3       # Thấp → dịch chính xác hơn, ít sáng tạo
    num_ctx: int = 4096            # Context window size
    timeout: int = 120             # Timeout (giây) cho mỗi request

    # Translation-specific
    max_input_length: int = 2048   # Giới hạn input text (characters)
    batch_size: int = 4            # Số câu dịch song song (nếu batch)

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Tạo config từ biến môi trường."""
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.3")),
            num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "4096")),
            timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
            max_input_length=int(os.getenv("OLLAMA_MAX_INPUT_LENGTH", "2048")),
            batch_size=int(os.getenv("OLLAMA_BATCH_SIZE", "4")),
        )
