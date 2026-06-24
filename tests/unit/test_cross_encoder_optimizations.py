from backend import qa_loop


def test_get_cross_encoder_returns_none_on_load_failure(mocker):
    """When the loader raises, _get_cross_encoder swallows it and returns None.

    This is the only real branch in the function (the success path is a plain
    passthrough of load_reranker()'s result).
    """
    mocker.patch("backend.qa_loop.load_reranker", side_effect=RuntimeError("model unavailable"))

    assert qa_loop._get_cross_encoder() is None
