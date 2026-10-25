import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

output_path = ROOT / "openapi.json"
output_path.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"Wrote {output_path.relative_to(ROOT.parent)}")
