from dataclasses import dataclass
from io import BytesIO
from typing import Protocol
import socket
import struct
import unicodedata
import zipfile

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.sources.documents import clean_text


MAX_ASSET_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 100_000_000


@dataclass(frozen=True)
class SniffedAsset:
    asset_type: str
    content_type: str
    normalized_bytes: bytes
    text: str | None
    metadata_stripped: bool


def sniff_and_normalize(contents: bytes) -> SniffedAsset:
    if not contents:
        raise HTTPException(status_code=422, detail="The uploaded asset is empty.")
    if len(contents) > MAX_ASSET_BYTES:
        raise HTTPException(status_code=413, detail="Campaign assets must be 25 MB or smaller.")
    if contents.startswith(b"%PDF-"):
        return SniffedAsset("document", "application/pdf", contents, None, False)
    if contents.startswith(b"PK\x03\x04"):
        if not zipfile.is_zipfile(BytesIO(contents)):
            raise HTTPException(status_code=415, detail="This ZIP-based file is invalid.")
        with zipfile.ZipFile(BytesIO(contents)) as archive:
            expanded = sum(item.file_size for item in archive.infolist())
            names = archive.namelist()
            if "word/document.xml" not in names or expanded > 100 * 1024 * 1024 or expanded > len(contents) * 100:
                raise HTTPException(status_code=415, detail="Only safe, valid DOCX campaign assets are supported.")
        return SniffedAsset("document", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", contents, None, False)
    try:
        image = Image.open(BytesIO(contents))
        image_format = (image.format or "").upper()
        if image_format not in {"PNG", "JPEG", "WEBP"}:
            raise HTTPException(status_code=415, detail="Image assets must be PNG, JPEG, or WebP.")
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise HTTPException(status_code=413, detail="This image is too large to process safely.")
        image.verify()
        image = ImageOps.exif_transpose(Image.open(BytesIO(contents)))
        if image_format == "JPEG" and image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        output = BytesIO()
        image.save(output, format=image_format, optimize=True, exif=b"")
        content_type = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[image_format]
        normalized = output.getvalue()
        if len(normalized) > MAX_ASSET_BYTES:
            raise HTTPException(status_code=413, detail="The normalized image is larger than the asset size limit.")
        return SniffedAsset("image", content_type, normalized, None, True)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        pass
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="The file contents are not a supported image, PDF, DOCX, or UTF-8 text asset.") from exc
    text = clean_text(text).strip()
    if not text or sum(unicodedata.category(char) == "Cc" and char not in "\n\t\r" for char in text) > len(text) * 0.01:
        raise HTTPException(status_code=415, detail="The file contents are not readable UTF-8 text.")
    return SniffedAsset("document", "text/markdown", contents, text, False)


def difference_hash(image_bytes: bytes) -> int:
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(image.tobytes())
    result = 0
    for y in range(8):
        for x in range(8):
            result = (result << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return result


def similarity(left: int, right: int) -> float:
    return 1.0 - (left ^ right).bit_count() / 64


class OCRProvider(Protocol):
    name: str

    def extract(self, image_bytes: bytes) -> str: ...


class TesseractOCR:
    name = "tesseract"

    def extract(self, image_bytes: bytes) -> str:
        import pytesseract

        settings = get_settings()
        if settings.tesseract_command:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_command
        image = Image.open(BytesIO(image_bytes))
        return clean_text(pytesseract.image_to_string(image, timeout=settings.tesseract_timeout_seconds)).strip()


def get_ocr_provider() -> OCRProvider | None:
    if get_settings().ocr_provider.lower() == "tesseract":
        return TesseractOCR()
    return None


def scan_for_malware(contents: bytes) -> str:
    settings = get_settings()
    if not settings.malware_scanner_host:
        return "not_configured"
    try:
        with socket.create_connection((settings.malware_scanner_host, settings.malware_scanner_port), timeout=settings.malware_scan_timeout_seconds) as client:
            client.settimeout(settings.malware_scan_timeout_seconds)
            client.sendall(b"zINSTREAM\0")
            for offset in range(0, len(contents), 64 * 1024):
                chunk = contents[offset:offset + 64 * 1024]
                client.sendall(struct.pack("!I", len(chunk)) + chunk)
            client.sendall(struct.pack("!I", 0))
            response = client.recv(4096).decode("utf-8", "replace")
    except OSError as exc:
        raise HTTPException(status_code=503, detail="The configured malware scanner is unavailable. The asset was not saved.") from exc
    if "FOUND" in response:
        raise HTTPException(status_code=422, detail="The malware scanner rejected this asset.")
    if "OK" not in response:
        raise HTTPException(status_code=503, detail="The malware scanner did not return a valid result. The asset was not saved.")
    return "clean"
