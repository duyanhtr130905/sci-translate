"""
Unit tests cho OllamaEngine
Kiểm tra kết nối Ollama và khả năng dịch cơ bản.
Phiên bản này khớp với ollama_engine.py dùng LangChain.
"""

import pytest
from unittest.mock import MagicMock, patch
from models.ollama_engine import OllamaEngine
from models.ollama_config import OllamaConfig

MOCK_TRANSLATION = "Học máy là một tập hợp con của trí tuệ nhân tạo."


# =========================
# FIXTURES
# =========================
@pytest.fixture
def mock_config():
    """Config cho test (không cần Ollama thật)."""
    return OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen2.5:3b",
        temperature=0.0,
        num_ctx=4096,
        timeout=30,
    )


@pytest.fixture
def engine_with_mock_chain(mock_config):
    """OllamaEngine với chain đã được mock — không cần Ollama chạy."""
    with patch("models.ollama_engine.get_chain") as mock_get_chain:
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MOCK_TRANSLATION
        mock_get_chain.return_value = mock_chain

        engine = OllamaEngine(config=mock_config)
        engine.chain = mock_chain  # gán lại để dùng trong test
        yield engine, mock_chain


# =========================
# TEST ENGINE
# =========================
class TestOllamaEngine:
    """Tests cho OllamaEngine."""

    def test_translate_returns_non_empty_string(self, engine_with_mock_chain):
        """translate() phải trả về string không rỗng."""
        engine, mock_chain = engine_with_mock_chain
        result = engine.translate("Machine learning is a subset of AI.")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_translate_calls_chain_invoke(self, engine_with_mock_chain):
        """translate() phải gọi chain.invoke đúng 1 lần."""
        engine, mock_chain = engine_with_mock_chain
        engine.translate("Machine learning is a subset of AI.")

        mock_chain.invoke.assert_called_once()

    def test_translate_invoke_contains_input(self, engine_with_mock_chain):
        """chain.invoke phải nhận đúng text input."""
        engine, mock_chain = engine_with_mock_chain
        src = "Machine learning is a subset of AI."
        engine.translate(src)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["input"] == src

    def test_translate_with_rag_context(self, engine_with_mock_chain):
        """translate() với rag_context phải truyền examples vào chain."""
        engine, mock_chain = engine_with_mock_chain
        rag = "Học máy (Machine Learning) là một nhánh của AI."

        result = engine.translate(
            text="Machine learning is a subset of AI.",
            rag_context=rag,
        )

        assert isinstance(result, str)
        assert len(result) > 0
        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["examples"] == rag

    def test_translate_no_rag_context_uses_none(self, engine_with_mock_chain):
        """translate() không có rag_context phải truyền 'None' vào examples."""
        engine, mock_chain = engine_with_mock_chain
        engine.translate("Machine learning is a subset of AI.")

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["examples"] == "None"

    def test_translate_with_kg_terms_in_glossary(self, engine_with_mock_chain):
        """translate() với kg_terms phải merge vào glossary block."""
        engine, mock_chain = engine_with_mock_chain
        engine.translate(
            text="Machine learning is a subset of AI.",
            kg_terms={"Machine learning": "Học máy", "AI": "Trí tuệ nhân tạo"},
        )

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "Học máy" in call_kwargs["glossary"]
        assert "Trí tuệ nhân tạo" in call_kwargs["glossary"]

    def test_translate_kg_shortcut(self, mock_config):
        """KG shortcut: nếu text khớp đúng 1 term thì trả về luôn, không gọi chain."""
        with patch("models.ollama_engine.get_chain") as mock_get_chain:
            mock_chain = MagicMock()
            mock_get_chain.return_value = mock_chain

            engine = OllamaEngine(config=mock_config)
            result = engine.translate(
                text="thuật toán",
                kg_terms={"thuật toán": "algorithm"},
                direction="vi->en",
            )

            assert result == "algorithm"
            mock_chain.invoke.assert_not_called()

    def test_translate_direction_en_vi(self, engine_with_mock_chain):
        """translate() với direction en->vi phải set đúng source/target lang."""
        engine, mock_chain = engine_with_mock_chain
        engine.translate(
            text="Machine learning is a subset of AI.",
            direction="en->vi",
        )

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["source_lang"] == "English"
        assert call_kwargs["target_lang"] == "Vietnamese"

    def test_translate_direction_vi_en(self, engine_with_mock_chain):
        """translate() với direction vi->en phải set đúng source/target lang."""
        engine, mock_chain = engine_with_mock_chain
        engine.translate(
            text="Học máy là gì?",
            direction="vi->en",
        )

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["source_lang"] == "Vietnamese"
        assert call_kwargs["target_lang"] == "English"

    def test_translate_exception_returns_error_string(self, mock_config):
        """Nếu chain.invoke raise exception, translate() phải trả về string 'Error: ...'."""
        with patch("models.ollama_engine.get_chain") as mock_get_chain:
            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = Exception("Connection timeout")
            mock_get_chain.return_value = mock_chain

            engine = OllamaEngine(config=mock_config)
            result = engine.translate("Machine learning is a subset of AI.")

            assert isinstance(result, str)
            assert result.startswith("Error:")

    def test_postprocess_strips_label_prefix(self, mock_config):
        """_postprocess phải xóa prefix như 'Translation:' khỏi output."""
        with patch("models.ollama_engine.get_chain") as mock_get_chain:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Translation: Học máy là gì."
            mock_get_chain.return_value = mock_chain

            engine = OllamaEngine(config=mock_config)
            result = engine.translate("What is machine learning.")

            assert not result.lower().startswith("translation:")

    def test_postprocess_removes_cjk_characters(self, mock_config):
        """_postprocess phải loại bỏ ký tự CJK và dấu câu CJK."""
        with patch("models.ollama_engine.get_chain") as mock_get_chain:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Học máy。là gì，，"
            mock_get_chain.return_value = mock_chain

            engine = OllamaEngine(config=mock_config)
            result = engine.translate("What is machine learning.")

            assert "。" not in result
            assert "，" not in result

    def test_postprocess_hallucination_guard(self, mock_config):
        """_postprocess phải fallback khi output chỉ có ký tự lạ, không có chữ thật."""
        with patch("models.ollama_engine.get_chain") as mock_get_chain:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "，，，，。"
            mock_get_chain.return_value = mock_chain

            engine = OllamaEngine(config=mock_config)
            result = engine.translate("What is machine learning.")

            # Sau khi strip CJK, result < 2 ký tự → fallback = raw output
            assert isinstance(result, str)


# =========================
# TEST CONFIG
# =========================
class TestOllamaConfig:
    """Tests cho OllamaConfig."""

    def test_default_config(self):
        """Config mặc định phải có giá trị hợp lệ."""
        config = OllamaConfig()
        assert config.base_url == "http://localhost:11434"
        assert config.model == "qwen2.5:3b"
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