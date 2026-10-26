from __future__ import annotations

import re
import secrets
import sys
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    values = {
        "APP_SECRET_KEY": secrets.token_urlsafe(48),
        "BOOTSTRAP_ADMIN_PASSWORD": secrets.token_urlsafe(36),
        "MINIO_ROOT_PASSWORD": secrets.token_urlsafe(32),
        "S3_SECRET_ACCESS_KEY": secrets.token_urlsafe(32),
    }
    for key, value in values.items():
        text, replacements = re.subn(rf"(?m)^{key}=.*$", f"{key}={value}", text)
        if replacements != 1:
            raise SystemExit(f"Expected one {key} setting in {path}.")
    path.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
