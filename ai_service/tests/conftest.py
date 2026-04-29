"""
Test fixtures — Shared fixtures cho tất cả test files.
Mock Ollama client, DB session, và các dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client — không cần Ollama daemon thật."""
    client = MagicMock()

    # Mock chat response
    mock_response = MagicMock()
    mock_response.message.content = "Đây là bản dịch mẫu."
    client.chat.return_value = mock_response

    # Mock list response
    mock_model = MagicMock()
    mock_model.model = "gemma2"
    mock_models = MagicMock()
    mock_models.models = [mock_model]
    client.list.return_value = mock_models

    return client


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    yield session
    session.close()


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver."""
    driver = MagicMock()
    yield driver
    driver.close()


@pytest.fixture
def mock_chromadb_client():
    """Mock ChromaDB client."""
    client = MagicMock()
    collection = MagicMock()
    collection.query.return_value = {
        "documents": [["Example parallel sentence from corpus."]],
        "distances": [[0.15]],
        "metadatas": [[{"source": "test_corpus"}]],
    }
    client.get_or_create_collection.return_value = collection
    return client
