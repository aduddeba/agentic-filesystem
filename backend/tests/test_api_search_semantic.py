def test_create_file_is_auto_indexed(pg_client):
    response = pg_client.post(
        "/api/files", json={"path": "cat.txt", "type": "file", "content": "the cat sat on the mat"}
    )
    assert response.status_code == 201

    results = pg_client.get("/api/files/search/semantic", params={"q": "a feline resting on a rug"}).json()

    assert any(r["path"] == "cat.txt" for r in results)


def test_update_file_content_reindexes(pg_client):
    pg_client.post("/api/files", json={"path": "note.txt", "type": "file", "content": "quarterly revenue report"})
    pg_client.put("/api/files/content", params={"path": "note.txt"}, json={"content": "a feline resting on a rug"})

    results = pg_client.get("/api/files/search/semantic", params={"q": "the cat sat on the mat"}).json()

    assert any(r["path"] == "note.txt" for r in results)


def test_rename_preserves_searchability(pg_client):
    pg_client.post("/api/files", json={"path": "old.txt", "type": "file", "content": "the cat sat on the mat"})
    pg_client.patch("/api/files", json={"path": "old.txt", "new_path": "new.txt"})

    results = pg_client.get("/api/files/search/semantic", params={"q": "a feline resting on a rug"}).json()

    assert any(r["path"] == "new.txt" for r in results)
    assert not any(r["path"] == "old.txt" for r in results)


def test_reindex_endpoint_picks_up_out_of_band_file(pg_client, tmp_path):
    pg_client.post("/api/files", json={"path": "a.txt", "type": "file", "content": "placeholder"})

    # simulate a file dropped in outside the app (e.g. via VSCode), bypassing the API
    (tmp_path / "ghost.txt").write_text("the cat sat on the mat", encoding="utf-8")

    response = pg_client.post("/api/files/reindex")

    assert response.status_code == 200
    assert response.json()["indexed"] == 2

    results = pg_client.get("/api/files/search/semantic", params={"q": "a feline resting on a rug"}).json()
    assert any(r["path"] == "ghost.txt" for r in results)


def test_semantic_search_finds_paraphrase_not_just_keywords(pg_client):
    pg_client.post("/api/files", json={"path": "cat.txt", "type": "file", "content": "the cat sat on the mat"})
    pg_client.post(
        "/api/files", json={"path": "finance.txt", "type": "file", "content": "quarterly revenue increased by ten percent"}
    )

    results = pg_client.get(
        "/api/files/search/semantic", params={"q": "a feline resting on a rug", "mode": "vector"}
    ).json()

    assert results[0]["path"] == "cat.txt"


def test_hybrid_mode_surfaces_exact_keyword_hit(pg_client):
    pg_client.post(
        "/api/files", json={"path": "log.txt", "type": "file", "content": "ERROR: connection refused to xyzzy123"}
    )
    pg_client.post("/api/files", json={"path": "other.txt", "type": "file", "content": "unrelated content entirely"})

    results = pg_client.get("/api/files/search/semantic", params={"q": "xyzzy123", "mode": "hybrid"}).json()

    assert any(r["path"] == "log.txt" for r in results)


def test_hybrid_mode_surfaces_filename_match(pg_client):
    pg_client.post(
        "/api/files", json={"path": "README.md", "type": "file", "content": "# Agentic AI File System\n\nProject overview."}
    )
    pg_client.post(
        "/api/files", json={"path": "unrelated.txt", "type": "file", "content": "nothing to do with the query"}
    )

    results = pg_client.get("/api/files/search/semantic", params={"q": "README", "mode": "hybrid"}).json()

    assert any(r["path"] == "README.md" for r in results)


def test_semantic_search_blank_query_returns_empty_list(pg_client):
    response = pg_client.get("/api/files/search/semantic", params={"q": "  "})

    assert response.status_code == 200
    assert response.json() == []
