from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing_extensions import Annotated


CampaignName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=240)]
CampaignChannel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=50)]


class CampaignCreate(BaseModel):
    name: CampaignName
    channels: list[CampaignChannel] = Field(min_length=1, max_length=10)
    starts_at: date | None = None
    ends_at: date | None = None
    language: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=32)] = "en"

    @model_validator(mode="after")
    def check_dates_and_channels(self):
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("Campaign end date must be on or after its start date.")
        if len({channel.casefold() for channel in self.channels}) != len(self.channels):
            raise ValueError("Campaign channels must be unique.")
        return self


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_group_id: str
    version: int
    current: bool
    supersedes_asset_id: str | None
    asset_type: str
    channel: str
    language: str
    content_type: str
    original_filename: str | None
    sha256: str
    size_bytes: int
    malware_status: str
    extraction_status: str
    metadata_stripped: bool
    text_content: str | None
    extracted_text: str | None
    logo_matches: list[dict[str, Any]]
    created_at: datetime


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    channels: list[str]
    starts_at: date | None
    ends_at: date | None
    language: str
    planned_publish_date: datetime | None
    status: str
    version: int
    created_at: datetime


class CampaignDetailResponse(CampaignResponse):
    assets: list[AssetResponse]
