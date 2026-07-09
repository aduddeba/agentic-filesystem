from tools.embeddings import EMBEDDING_DIM, embed_passages, embed_query


def test_embed_passages_returns_one_vector_per_text():
    vectors = embed_passages(["hello world", "goodbye world"])

    assert len(vectors) == 2
    assert all(len(v) == EMBEDDING_DIM for v in vectors)


def test_embed_passages_empty_list_returns_empty_list():
    assert embed_passages([]) == []


def test_embed_query_returns_single_vector_of_expected_dimension():
    vector = embed_query("what is the capital of France?")

    assert len(vector) == EMBEDDING_DIM


def test_embeddings_are_unit_normalized():
    vector = embed_query("some text to embed")

    magnitude = sum(v * v for v in vector) ** 0.5

    assert abs(magnitude - 1.0) < 1e-4


def test_identical_text_embeds_deterministically():
    a = embed_passages(["the quick brown fox"])[0]
    b = embed_passages(["the quick brown fox"])[0]

    assert a == b


def test_similar_texts_are_closer_than_unrelated_texts():
    def cosine_similarity(a, b):
        return sum(x * y for x, y in zip(a, b))

    cat_a, cat_b, unrelated = embed_passages(
        ["the cat sat on the mat", "a feline resting on a rug", "quarterly revenue increased by ten percent"]
    )

    assert cosine_similarity(cat_a, cat_b) > cosine_similarity(cat_a, unrelated)
