from app import config as config_module


def _arm_storage_root_restore(monkeypatch):
    # Registers the pre-test value with monkeypatch so it's restored on
    # teardown, even though set_storage_root() reassigns the attribute
    # directly afterward rather than through monkeypatch itself.
    monkeypatch.setattr(config_module.settings, "storage_root", config_module.settings.storage_root)


def test_set_storage_root_updates_in_memory_setting(tmp_path, monkeypatch):
    _arm_storage_root_restore(monkeypatch)
    env_path = tmp_path / ".env"
    env_path.write_text("STORAGE_ROOT=/old/path\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "_ENV_PATH", env_path)

    config_module.set_storage_root("/new/path")

    assert config_module.settings.storage_root == "/new/path"


def test_set_storage_root_rewrites_existing_line_preserving_others(tmp_path, monkeypatch):
    _arm_storage_root_restore(monkeypatch)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DATABASE_URL=postgresql://x\nSTORAGE_ROOT=/old/path\nCORS_ORIGINS=http://localhost:3000\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "_ENV_PATH", env_path)

    config_module.set_storage_root("/new/path")

    assert env_path.read_text(encoding="utf-8").splitlines() == [
        "DATABASE_URL=postgresql://x",
        "STORAGE_ROOT=/new/path",
        "CORS_ORIGINS=http://localhost:3000",
    ]


def test_set_storage_root_appends_line_when_missing(tmp_path, monkeypatch):
    _arm_storage_root_restore(monkeypatch)
    env_path = tmp_path / ".env"
    env_path.write_text("DATABASE_URL=postgresql://x\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "_ENV_PATH", env_path)

    config_module.set_storage_root("/new/path")

    assert env_path.read_text(encoding="utf-8").splitlines() == [
        "DATABASE_URL=postgresql://x",
        "STORAGE_ROOT=/new/path",
    ]


def test_set_storage_root_creates_env_file_if_missing(tmp_path, monkeypatch):
    _arm_storage_root_restore(monkeypatch)
    env_path = tmp_path / ".env"
    monkeypatch.setattr(config_module, "_ENV_PATH", env_path)

    config_module.set_storage_root("/new/path")

    assert env_path.read_text(encoding="utf-8") == "STORAGE_ROOT=/new/path\n"
