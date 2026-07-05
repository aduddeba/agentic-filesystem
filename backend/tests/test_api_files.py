import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app import config as config_module
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    # main.py's lifespan touches the module-level `engine`/`SessionLocal` directly
    # (not through the `get_db` dependency), so it must be redirected too --
    # otherwise app startup would try to open a real Postgres connection.
    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(main_module, "SessionLocal", TestingSessionLocal)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_tree_and_stats(client):
    assert client.get("/api/files/tree").json() == []
    assert client.get("/api/files/stats").json() == {
        "file_count": 0,
        "directory_count": 0,
        "total_size": 0,
    }


def test_create_file_appears_in_tree_and_stats(client):
    response = client.post("/api/files", json={"path": "note.txt", "type": "file", "content": "hello"})

    assert response.status_code == 201
    body = response.json()
    assert body == {"path": "note.txt", "name": "note.txt", "is_dir": False, "depth": 0, "size": 5}

    tree = client.get("/api/files/tree").json()
    assert tree == [body]

    stats = client.get("/api/files/stats").json()
    assert stats == {"file_count": 1, "directory_count": 0, "total_size": 5}


def test_create_directory(client):
    response = client.post("/api/files", json={"path": "docs", "type": "directory"})

    assert response.status_code == 201
    assert response.json()["is_dir"] is True

    stats = client.get("/api/files/stats").json()
    assert stats["directory_count"] == 1


def test_create_nested_file_creates_parent_directory_records(client):
    client.post("/api/files", json={"path": "a/b/note.txt", "type": "file", "content": "hi"})

    stats = client.get("/api/files/stats").json()

    assert stats == {"file_count": 1, "directory_count": 2, "total_size": 2}


def test_create_duplicate_path_returns_409(client):
    client.post("/api/files", json={"path": "note.txt", "type": "file", "content": "hello"})

    response = client.post("/api/files", json={"path": "note.txt", "type": "file", "content": "again"})

    assert response.status_code == 409


def test_read_file_content(client):
    client.post("/api/files", json={"path": "note.txt", "type": "file", "content": "hello world"})

    response = client.get("/api/files/content", params={"path": "note.txt"})

    assert response.status_code == 200
    assert response.json() == {"path": "note.txt", "content": "hello world"}


def test_read_missing_file_returns_404(client):
    response = client.get("/api/files/content", params={"path": "missing.txt"})

    assert response.status_code == 404


def test_update_file_content(client):
    client.post("/api/files", json={"path": "note.txt", "type": "file", "content": "old"})

    response = client.put("/api/files/content", params={"path": "note.txt"}, json={"content": "new content"})

    assert response.status_code == 200
    assert response.json()["size"] == len("new content")
    assert client.get("/api/files/content", params={"path": "note.txt"}).json()["content"] == "new content"


def test_update_missing_file_returns_404(client):
    response = client.put("/api/files/content", params={"path": "missing.txt"}, json={"content": "x"})

    assert response.status_code == 404


def test_delete_file(client):
    client.post("/api/files", json={"path": "note.txt", "type": "file", "content": "hello"})

    response = client.delete("/api/files", params={"path": "note.txt"})

    assert response.status_code == 204
    assert client.get("/api/files/tree").json() == []


def test_delete_directory_removes_descendant_records(client):
    client.post("/api/files", json={"path": "dir/note.txt", "type": "file", "content": "hi"})

    response = client.delete("/api/files", params={"path": "dir"})

    assert response.status_code == 204
    assert client.get("/api/files/tree").json() == []
    assert client.get("/api/files/stats").json() == {"file_count": 0, "directory_count": 0, "total_size": 0}


def test_delete_missing_path_returns_404(client):
    response = client.delete("/api/files", params={"path": "missing.txt"})

    assert response.status_code == 404


def test_rename_file(client):
    client.post("/api/files", json={"path": "old.txt", "type": "file", "content": "hi"})

    response = client.patch("/api/files", json={"path": "old.txt", "new_path": "new.txt"})

    assert response.status_code == 200
    assert response.json()["path"] == "new.txt"
    assert client.get("/api/files/content", params={"path": "old.txt"}).status_code == 404
    assert client.get("/api/files/content", params={"path": "new.txt"}).json()["content"] == "hi"


def test_rename_missing_path_returns_404(client):
    response = client.patch("/api/files", json={"path": "missing.txt", "new_path": "new.txt"})

    assert response.status_code == 404


def test_rename_onto_existing_path_returns_409(client):
    client.post("/api/files", json={"path": "a.txt", "type": "file", "content": "a"})
    client.post("/api/files", json={"path": "b.txt", "type": "file", "content": "b"})

    response = client.patch("/api/files", json={"path": "a.txt", "new_path": "b.txt"})

    assert response.status_code == 409


@pytest.mark.parametrize("path", ["../escape.txt", "/etc/passwd", "a/../../escape.txt"])
def test_path_traversal_is_rejected(client, path):
    response = client.get("/api/files/content", params={"path": path})

    assert response.status_code == 400


def test_search_finds_matches(client):
    client.post("/api/files", json={"path": "a.txt", "type": "file", "content": "needle in a haystack"})
    client.post("/api/files", json={"path": "sub/b.txt", "type": "file", "content": "no match here"})

    response = client.get("/api/files/search", params={"q": "needle"})

    assert response.status_code == 200
    matches = response.json()
    assert len(matches) == 1
    assert matches[0]["path"] == "a.txt"
    assert matches[0]["line"] == 1


def test_search_blank_query_returns_empty_list(client):
    response = client.get("/api/files/search", params={"q": "  "})

    assert response.status_code == 200
    assert response.json() == []
