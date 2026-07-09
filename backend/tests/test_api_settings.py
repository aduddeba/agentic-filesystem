"""Tests for GET/PUT /api/settings.

Uses `pg_client` (real Postgres), not the SQLite `client` fixture, because
PUT /api/settings calls index_pending() -> index_file(), which inserts Chunk
rows through pgvector's Postgres-only Vector column type.
"""

import pytest

from app import config as config_module


@pytest.fixture(autouse=True)
def _isolate_env_file(tmp_path, monkeypatch):
    # PUT /api/settings persists via set_storage_root(), which writes to
    # config_module._ENV_PATH -- redirect it so tests never touch the real
    # backend/.env.
    monkeypatch.setattr(config_module, "_ENV_PATH", tmp_path / ".env.test")


def test_get_settings_returns_current_root(pg_client):
    response = pg_client.get("/api/settings")

    assert response.status_code == 200
    assert response.json()["storage_root"] == config_module.settings.storage_root


def test_put_settings_rejects_relative_path(pg_client):
    response = pg_client.put("/api/settings", json={"storage_root": "relative/path"})

    assert response.status_code == 400


def test_put_settings_rejects_path_that_is_a_file(pg_client, tmp_path):
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("x", encoding="utf-8")

    response = pg_client.put("/api/settings", json={"storage_root": str(file_path)})

    assert response.status_code == 400


def test_put_settings_switches_root_and_creates_directory(pg_client, tmp_path):
    new_root = tmp_path / "elsewhere"

    response = pg_client.put("/api/settings", json={"storage_root": str(new_root)})

    assert response.status_code == 200
    assert response.json()["storage_root"] == str(new_root)
    assert new_root.is_dir()


def test_put_settings_tree_reflects_new_location(pg_client, tmp_path):
    new_root = tmp_path / "elsewhere"
    new_root.mkdir()
    (new_root / "hello.txt").write_text("hi", encoding="utf-8")

    pg_client.put("/api/settings", json={"storage_root": str(new_root)})

    tree = pg_client.get("/api/files/tree").json()
    assert any(node["path"] == "hello.txt" for node in tree)


def test_put_settings_persists_to_env_file(pg_client, tmp_path):
    new_root = tmp_path / "elsewhere"

    pg_client.put("/api/settings", json={"storage_root": str(new_root)})

    env_text = config_module._ENV_PATH.read_text(encoding="utf-8")
    assert f"STORAGE_ROOT={new_root}" in env_text
