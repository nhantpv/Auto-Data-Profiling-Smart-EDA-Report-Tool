import os

from config.env_loader import load_project_dotenv


def test_load_project_dotenv_reads_root_env(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("SMART_EDA_TEST_DOTENV=loaded\n", encoding="utf-8")
    monkeypatch.delenv("SMART_EDA_TEST_DOTENV", raising=False)

    assert load_project_dotenv(tmp_path) is True
    assert os.environ["SMART_EDA_TEST_DOTENV"] == "loaded"


def test_load_project_dotenv_does_not_override_existing_env(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("SMART_EDA_TEST_DOTENV=from_file\n", encoding="utf-8")
    monkeypatch.setenv("SMART_EDA_TEST_DOTENV", "from_process")

    load_project_dotenv(tmp_path)

    assert os.environ["SMART_EDA_TEST_DOTENV"] == "from_process"
