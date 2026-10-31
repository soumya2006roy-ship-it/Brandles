"""Create a valid PNG that exceeds the visual upload size limit for browser verification."""

from pathlib import Path

from PIL import Image


OUTPUT = Path(__file__).resolve().parent / "tmp" / "oversized.png"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # A flat 3,100 x 3,100 RGB image with compression disabled is valid and
    # reliably larger than the 25 MiB API limit without requiring random data.
    Image.new("RGB", (3_100, 3_100), (30, 63, 53)).save(OUTPUT, format="PNG", compress_level=0)
    if OUTPUT.stat().st_size <= 25 * 1024 * 1024:
        raise RuntimeError("Oversized fixture did not exceed the API's 25 MiB upload limit.")


if __name__ == "__main__":
    main()
