"""Check mounted AITCHazard credentials without printing secret values."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aitchazard.credentials import check_credentials  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="mars", help="Credential profile label for reporting.")
    parser.add_argument("--credentials-dir", help="Optional mounted credentials directory.")
    parser.add_argument(
        "--require",
        action="store_true",
        help="Exit non-zero when no credential handles are found.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = check_credentials(profile=args.profile, credentials_dir=args.credentials_dir)
    print(result.summary())
    print("Searched directories:")
    for directory in result.searched_dirs:
        print(f"- {directory}")
    if args.require and not result.ok:
        print("No credential handles found. Mount files or export environment variables before real mode.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
