"""
Unit tests cho OllamaEngine
Kiểm tra kết nối Ollama và khả năng dịch cơ bản.
"""

import pytest
from unittest.mock import MagicMock, patch
from models.ollama_engine import OllamaEngine
from models.ollama_config import OllamaConfig


@pytest.fixture
def mock_config():
    """Config cho test (không cần Ollama thật)."""
    return OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen2.5:7b",
        temperature=0.3,
        num_ctx=4096,
        timeout=30,
    )


@pytest.fixture
def mock_ollama_response():
    """Mock response từ Ollama API."""
    mock = MagicMock()
    mock.message.content = "Học máy là một tập hợp con của trí tuệ nhân tạo."
    return mock


class TestOllamaEngine:
    """Tests cho OllamaEngine."""

    def test_translate_returns_non_empty_string(self, mock_config, mock_ollama_response):
        """translate() phải trả về string không rỗng."""
        with patch("models.ollama_engine.ollama_sdk") as mock_sdk:
            mock_client = MagicMock()
            mock_client.chat.return_value = mock_ollama_response
            mock_sdk.Client.return_value = mock_client

            engine = OllamaEngine(config=mock_config)
            result = engine.translate("Machine learning is a subset of AI.")

            assert isinstance(result, str)
            assert len(result) > 0

    def test_translate_with_rag_context(self, mock_config, mock_ollama_response):
        """translate() với RAG context phải inject context vào prompt."""
        with patch("models.ollama_engine.ollama_sdk") as mock_sdk:
            mock_client = MagicMock()
            mock_client.chat.return_value = mock_ollama_response
            mock_sdk.Client.return_value = mock_client

            engine = OllamaEngine(config=mock_config)
            result = engine.translate(
                text="Machine learning is a subset of AI.",
                rag_context="Học máy (Machine Learning) là một nhánh của AI.",
            )

            assert isinstance(result, str)
            assert len(result) > 0
            # Kiểm tra prompt đã chứa RAG context
            call_args = mock_client.chat.call_args
            user_msg = call_args.kwargs["messages"][1]["content"]
            assert "Tham khảo" in user_msg

    def test_translate_with_kg_terms(self, mock_config, mock_ollama_response):
        """translate() với KG terms phải inject thuật ngữ vào prompt."""
        with patch("models.ollama_engine.ollama_sdk") as mock_sdk:
            mock_client = MagicMock()
            mock_client.chat.return_value = mock_ollama_response
            mock_sdk.Client.return_value = mock_client

            engine = OllamaEngine(config=mock_config)
            result = engine.translate(
                text="Machine learning is a subset of AI.",
                kg_terms={"Machine learning": "Học máy", "AI": "Trí tuệ nhân tạo"},
            )

            assert isinstance(result, str)
            call_args = mock_client.chat.call_args
            user_msg = call_args.kwargs["messages"][1]["content"]
            assert "Học máy" in user_msg

    def test_translate_with_domain(self, mock_config, mock_ollama_response):
        """translate() với domain phải tạo system prompt phù hợp."""
        with patch("models.ollama_engine.ollama_sdk") as mock_sdk:
            mock_client = MagicMock()
            mock_client.chat.return_value = mock_ollama_response
            mock_sdk.Client.return_value = mock_client

            engine = OllamaEngine(config=mock_config)
            engine.translate(
                text="Neural networks mimic the brain.",
                domain="computer_science",
            )

            call_args = mock_client.chat.call_args
            system_msg = call_args.kwargs["messages"][0]["content"]
            assert "khoa học máy tính" in system_msg

    def test_health_check_ok(self, mock_config):
        """health_check() trả status ok khi model có sẵn."""
        with patch("models.ollama_engine.ollama_sdk") as mock_sdk:
            mock_client = MagicMock()
            mock_model = MagicMock()
            mock_model.model = "qwen2.5:7b"
            mock_models = MagicMock()
            mock_models.models = [mock_model]
            mock_client.list.return_value = mock_models
            mock_sdk.Client.return_value = mock_client

            engine = OllamaEngine(config=mock_config)
            result = engine.health_check()

            assert result["status"] == "ok"
            assert result["engine"] == "ollama"

    def test_health_check_error(self, mock_config):
        """health_check() trả status error khi Ollama không chạy."""
        with patch("models.ollama_engine.ollama_sdk") as mock_sdk:
            mock_client = MagicMock()
            mock_client.list.side_effect = ConnectionError("Ollama not running")
            mock_sdk.Client.return_value = mock_client

            engine = OllamaEngine(config=mock_config)
            result = engine.health_check()

            assert result["status"] == "error"


class TestOllamaConfig:
    """Tests cho OllamaConfig."""

    def test_default_config(self):
        """Config mặc định phải có giá trị hợp lệ."""
        config = OllamaConfig()
        assert config.base_url == "http://localhost:11434"
        assert config.model == "qwen2.5:7b"
        assert 0.0 <= config.temperature <= 2.0
        assert config.num_ctx > 0

    def test_from_env(self, monkeypatch):
        """from_env() phải đọc đúng biến môi trường."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://gpu-server:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5")
        monkeypatch.setenv("OLLAMA_TEMPERATURE", "0.1")

        config = OllamaConfig.from_env()

        assert config.base_url == "http://gpu-server:11434"
        assert config.model == "qwen2.5"
        assert config.temperature == 0.1
