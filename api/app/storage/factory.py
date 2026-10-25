from app.core.config import get_settings
from app.storage.interface import StorageDriver
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage


def get_storage() -> StorageDriver:
    if get_settings().file_storage_driver == "s3":
        return S3Storage()
    return LocalStorage()
