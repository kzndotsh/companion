from companion.core.vectors import from_blob, to_blob


def test_a_vector_survives_its_stored_bytes() -> None:
    v = (0.5, -0.25, 1.0)
    assert from_blob(to_blob(v)) == v
