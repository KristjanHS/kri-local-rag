"""Test the full QA pipeline from question to answer."""

from unittest.mock import MagicMock, patch

import pytest
from sentence_transformers import SentenceTransformer

from backend import config, qa_loop

# Mark the entire module as 'slow'
pytestmark = pytest.mark.slow


# --- Constants ---
EMBEDDING_MODEL = config.OLLAMA_EMBEDDING_MODEL
COLLECTION_NAME = config.COLLECTION_NAME


@pytest.fixture(scope="module")
def sample_documents():
    """Fixture for providing sample documents for ingestion."""
    return [
        "France is a country in Western Europe.",
        "The capital of France is Paris, known for its art and culture.",
        "The Eiffel Tower is a famous landmark in Paris.",
        "Germany is a country in Central Europe.",
        "Berlin is the capital of Germany.",
    ]


@pytest.fixture(scope="module")
def weaviate_collection_mock():
    """Fixture for mocking a Weaviate collection with pre-ingested data."""
    with patch("weaviate.connect_to_custom") as mock_connect:
        mock_client = MagicMock()
        mock_collection = MagicMock()

        # Mock is_ready and exists
        mock_client.is_ready.return_value = True
        mock_client.collections.exists.return_value = True

        # Mock the query interface
        mock_query = MagicMock()

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        # Simulate a hybrid search result
        mock_result = MagicMock()
        mock_result.objects = [MockObject("The capital of France is Paris.")]
        mock_query.hybrid.return_value = mock_result

        # Connect the mocks
        mock_collection.query = mock_query
        mock_client.collections.get.return_value = mock_collection
        mock_connect.return_value = mock_client

        # Provide a real embedding model for the retriever
        model = SentenceTransformer(EMBEDDING_MODEL)
        with patch("backend.retriever._get_embedding_model", return_value=model):
            yield mock_collection


@pytest.mark.integration
@patch("backend.qa_loop.Ollama")
def test_qa_pipeline_produces_answer(mock_ollama, weaviate_collection_mock):
    """Test the full QA pipeline to ensure a coherent answer is generated."""
    # Mock the Ollama LLM
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = "The capital of France is indeed Paris."
    mock_ollama.return_value = mock_llm

    # The user's question
    question = "What is the capital of France?"

    # Run the QA loop
    answer, sources = qa_loop.run_qa_loop(question, weaviate_collection_mock)

    # --- Assertions ---
    # Check that the retriever was called correctly
    weaviate_collection_mock.query.hybrid.assert_called_once()
    call_args = weaviate_collection_mock.query.hybrid.call_args
    assert call_args.kwargs["query"] == question
    assert "vector" in call_args.kwargs  # Ensure vector was passed

    # Check that the LLM was invoked with the right context
    mock_llm.invoke.assert_called_once()
    prompt = mock_llm.invoke.call_args[0][0]
    assert question in prompt
    assert "The capital of France is Paris." in prompt  # Check if context is in prompt

    # Check the final answer and sources
    assert "Paris" in answer
    assert "The capital of France is Paris." in sources


@pytest.mark.integration
def test_get_top_k_retrieves_correct_documents(weaviate_collection_mock):
    """Test that the retriever fetches the most relevant document."""
    from backend.retriever import get_top_k

    # The user's question
    question = "What is the capital of France?"

    # Run the retriever
    top_k_docs = get_top_k(question, k=1, collection=weaviate_collection_mock)

    # --- Assertions ---
    # Check that the query was executed
    weaviate_collection_mock.query.hybrid.assert_called_once()
    # Check that the correct document was returned
    assert len(top_k_docs) == 1
    assert "Paris" in top_k_docs[0]


@pytest.mark.integration
@patch("backend.qa_loop.Ollama")
def test_qa_pipeline_handles_no_context_gracefully(mock_ollama, weaviate_collection_mock):
    """Test how the QA pipeline behaves when the retriever finds no relevant documents."""
    # Mock the retriever to return no documents
    mock_query = weaviate_collection_mock.query
    mock_result = MagicMock()
    mock_result.objects = []  # No documents found
    mock_query.hybrid.return_value = mock_result

    # Mock the Ollama LLM
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = "I am sorry, but I do not have enough information to answer that question."
    mock_ollama.return_value = mock_llm

    # The user's question
    question = "What is the largest city in Australia?"

    # Run the QA loop
    answer, sources = qa_loop.run_qa_loop(question, weaviate_collection_mock)

    # --- Assertions ---
    # Check that the retriever was called
    weaviate_collection_mock.query.hybrid.assert_called_once()

    # Check that the LLM was still invoked but with a different prompt
    mock_llm.invoke.assert_called_once()
    prompt = mock_llm.invoke.call_args[0][0]
    assert "could not find any relevant information" in prompt.lower()

    # Check the final answer and sources
    assert "sorry" in answer.lower() or "do not have enough information" in answer.lower()
    assert len(sources) == 0


if __name__ == "__main__":
    pytest.main(["-s", __file__])
