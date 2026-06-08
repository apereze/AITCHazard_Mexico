from aitchazard.credentials import check_credentials
from aitchazard.block1.aifs_runner import run_real
from aitchazard.block1.config import load_block1_config


def test_missing_credentials_report_handles_without_values(tmp_path, monkeypatch):
    monkeypatch.delenv("AITCHAZARD_CREDENTIALS_DIR", raising=False)
    monkeypatch.delenv("ECMWF_API_KEY", raising=False)

    result = check_credentials(
        profile="mars",
        credentials_dir=str(tmp_path),
        accepted_files=(".ecmwfapirc",),
        accepted_env=("ECMWF_API_KEY",),
    )

    assert not result.ok
    assert "missing" in result.summary()
    assert "ECMWF_API_KEY=" not in result.summary()


def test_credential_file_presence_is_reported_without_reading_contents(tmp_path):
    credential_file = tmp_path / ".ecmwfapirc"
    credential_file.write_text("secret-token-should-not-appear", encoding="utf-8")

    result = check_credentials(
        profile="mars",
        credentials_dir=str(tmp_path),
        accepted_files=(".ecmwfapirc",),
        accepted_env=(),
    )

    assert result.ok
    assert str(credential_file) in result.found_files
    assert "secret-token-should-not-appear" not in result.summary()


def test_environment_credential_presence_reports_name_only(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_TOKEN", "hf_secret_value")

    result = check_credentials(
        profile="hf",
        credentials_dir=str(tmp_path),
        accepted_files=(),
        accepted_env=("HF_TOKEN",),
    )

    assert result.ok
    assert result.found_env == ("HF_TOKEN",)
    assert "hf_secret_value" not in result.summary()


def test_real_mode_rejects_hf_token_without_mars_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_TOKEN", "hf_secret_value")
    config = load_block1_config("conf/aitchazard_mexico/block1_aifs_single_v2.yaml")
    raw = dict(config.raw)
    raw["credentials"] = dict(config.raw["credentials"])
    raw["credentials"]["accepted_files"] = []
    raw["credentials"]["accepted_env"] = ["HF_TOKEN"]
    config = type(config)(raw=raw, path=config.path)

    try:
        run_real(config, credentials_dir=str(tmp_path))
    except RuntimeError as exc:
        assert "HF_TOKEN alone is not sufficient" in str(exc)
        assert "hf_secret_value" not in str(exc)
    else:
        raise AssertionError("run_real should reject HF-only credential handles")
