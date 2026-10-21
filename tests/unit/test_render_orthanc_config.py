"""Unit tests for src/utils/render_orthanc_config.py"""

import json
from pathlib import Path

import pytest

from src.utils.render_orthanc_config import main, render

pytestmark = pytest.mark.unit

TEMPLATES = sorted(Path(__file__).resolve().parents[2].glob("config/orthanc/*.template.json"))

# Characters that broke the old sed / str.replace substitution.
PASSWORDS = [
    "plain-password-123",
    "ab/cd+ef==",  # what `openssl rand -base64` produces
    "a&b",
    'pa"ss',
    "back\\slash",
    "${orthanc_user}",
    'x","RemoteAccessAllowed":false,"Evil":"1',
    "pässwörd-日本語",
]


@pytest.mark.parametrize("password", PASSWORDS)
@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.name)
def test_rendered_config_is_valid_json_with_the_exact_account(template, password):
    config = json.loads(render(template.read_text(), "orthanc", password))

    assert config["RegisteredUsers"] == {"orthanc": password}
    assert "Evil" not in config
    assert config["RemoteAccessAllowed"] is True


def test_user_is_escaped_too():
    template = '{"RegisteredUsers": {"${orthanc_user}": "${orthanc_password}"}}'

    assert json.loads(render(template, 'we"ird', "pw")) == {"RegisteredUsers": {'we"ird': "pw"}}


def test_a_value_is_never_substituted_a_second_time():
    template = '{"u": "${orthanc_user}", "p": "${orthanc_password}"}'

    assert json.loads(render(template, "${orthanc_password}", "secret")) == {
        "u": "${orthanc_password}",
        "p": "secret",
    }


def test_main_writes_the_rendered_file(tmp_path, monkeypatch):
    source = tmp_path / "in.json"
    target = tmp_path / "out.json"
    source.write_text('{"RegisteredUsers": {"${orthanc_user}": "${orthanc_password}"}}')
    monkeypatch.setenv("ORTHANC_USER", "orthanc")
    monkeypatch.setenv("ORTHANC_PASSWORD", 'ab/cd&ef"gh')

    assert main(["render", str(source), str(target)]) == 0

    assert json.loads(target.read_text()) == {"RegisteredUsers": {"orthanc": 'ab/cd&ef"gh'}}


@pytest.mark.parametrize("missing", ["ORTHANC_USER", "ORTHANC_PASSWORD"])
def test_main_fails_without_writing_when_the_account_is_missing(
    tmp_path, monkeypatch, capsys, missing
):
    source = tmp_path / "in.json"
    target = tmp_path / "out.json"
    source.write_text("{}")
    monkeypatch.setenv("ORTHANC_USER", "orthanc")
    monkeypatch.setenv("ORTHANC_PASSWORD", "pw")
    monkeypatch.delenv(missing)

    assert main(["render", str(source), str(target)]) == 1

    assert missing in capsys.readouterr().err
    assert not target.exists()


def test_main_rejects_an_empty_password(tmp_path, monkeypatch):
    source = tmp_path / "in.json"
    source.write_text("{}")
    monkeypatch.setenv("ORTHANC_USER", "orthanc")
    monkeypatch.setenv("ORTHANC_PASSWORD", "")

    assert main(["render", str(source), str(tmp_path / "out.json")]) == 1


def test_main_needs_both_paths(capsys):
    assert main(["render"]) == 2
