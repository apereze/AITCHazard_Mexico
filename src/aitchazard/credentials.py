"""Credential discovery helpers that never reveal secret values."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable


DEFAULT_CREDENTIAL_FILES = (".ecmwfapirc", ".cdsapirc", ".netrc")
DEFAULT_CREDENTIAL_ENV = (
    "ECMWF_API_URL",
    "ECMWF_API_KEY",
    "ECMWF_API_EMAIL",
    "CDSAPI_URL",
    "CDSAPI_KEY",
    "HF_TOKEN",
)


@dataclass(frozen=True)
class CredentialCheckResult:
    """Safe credential status report."""

    profile: str
    found_files: tuple[str, ...]
    found_env: tuple[str, ...]
    searched_dirs: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return bool(self.found_files or self.found_env)

    def summary(self) -> str:
        status = "ok" if self.ok else "missing"
        files = ", ".join(self.found_files) if self.found_files else "none"
        env = ", ".join(self.found_env) if self.found_env else "none"
        return f"{self.profile}: {status}; files={files}; env={env}"


def _candidate_dirs(credentials_dir: str | None = None) -> list[Path]:
    dirs: list[Path] = []
    if credentials_dir:
        dirs.append(Path(credentials_dir).expanduser())
    env_dir = os.environ.get("AITCHAZARD_CREDENTIALS_DIR")
    if env_dir:
        dirs.append(Path(env_dir).expanduser())
    home = Path.home()
    dirs.extend([home, home / ".config" / "earthkit"])

    seen: set[Path] = set()
    unique_dirs: list[Path] = []
    for directory in dirs:
        resolved = directory
        if resolved not in seen:
            seen.add(resolved)
            unique_dirs.append(resolved)
    return unique_dirs


def check_credentials(
    *,
    profile: str = "mars",
    credentials_dir: str | None = None,
    accepted_files: Iterable[str] = DEFAULT_CREDENTIAL_FILES,
    accepted_env: Iterable[str] = DEFAULT_CREDENTIAL_ENV,
) -> CredentialCheckResult:
    """Check whether usable credential handles exist without reading secrets."""
    dirs = _candidate_dirs(credentials_dir)
    found_files: list[str] = []
    for directory in dirs:
        for filename in accepted_files:
            path = directory / filename
            if path.is_file():
                found_files.append(str(path))

    found_env = [name for name in accepted_env if os.environ.get(name)]
    return CredentialCheckResult(
        profile=profile,
        found_files=tuple(found_files),
        found_env=tuple(found_env),
        searched_dirs=tuple(str(path) for path in dirs),
    )
