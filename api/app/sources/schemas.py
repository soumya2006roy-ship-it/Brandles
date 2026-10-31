from datetime import date, datetime
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing_extensions import Annotated


RuleType = Literal[
    "offer_name",
    "discount_percent",
    "valid_from",
    "valid_until",
    "banned_phrase",
    "required_disclaimer",
    "approved_logo",
    "channel_length_limit",
    "brand_colors",
    "typography",
]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    family_id: str
    title: str
    original_filename: str
    content_type: str
    sha256: str
    size_bytes: int
    version: int
    status: str
    effective_from: date | None
    effective_to: date | None
    created_by: str
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime


class SourcePassageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    page_number: int | None
    location_label: str | None
    start_offset: int | None
    end_offset: int | None


class PassageDetailResponse(SourcePassageResponse):
    source_id: str
    source_title: str
    source_version: int
    source_status: str


class SourceDetailResponse(SourceResponse):
    passages: list[SourcePassageResponse]


class SourceEffectiveDates(StrictInput):
    effective_from: date | None = None
    effective_to: date | None = None


class RuleWrite(StrictInput):
    rule_type: RuleType
    parameters: dict[str, Any] = Field(default_factory=dict)
    channel: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)] = None
    valid_from: date | None = None
    valid_to: date | None = None
    source_passage_id: str

    @model_validator(mode="after")
    def validate_parameters(self):
        value = self.parameters
        required_text = {"offer_name", "banned_phrase", "required_disclaimer"}
        if self.rule_type in required_text and not (isinstance(value.get("value"), str) and value["value"].strip()):
            raise ValueError("This rule type requires a non-empty 'value'.")
        if self.rule_type == "discount_percent":
            percent = value.get("percent")
            if not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
                raise ValueError("Discount percent must be between 0 and 100.")
        if self.rule_type in {"valid_from", "valid_until"}:
            try:
                date.fromisoformat(str(value.get("date", "")))
            except ValueError as exc:
                raise ValueError("Validity rules require a date in YYYY-MM-DD format.") from exc
        if self.rule_type == "approved_logo" and not (isinstance(value.get("version"), str) and value["version"].strip()):
            raise ValueError("Approved-logo rules require a version label.")
        if self.rule_type == "channel_length_limit":
            channel = value.get("channel")
            max_characters = value.get("max_characters")
            if not (isinstance(channel, str) and channel.strip() and isinstance(max_characters, int) and 1 <= max_characters <= 100000):
                raise ValueError("Channel limits require a channel and a positive max_characters value.")
        if self.rule_type == "brand_colors":
            colors = value.get("colors")
            if not isinstance(colors, list) or not 1 <= len(colors) <= 12 or any(not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in colors):
                raise ValueError("Brand colours require one to twelve hex colours such as #123456.")
            tolerance = value.get("tolerance_delta_e", 12)
            if not isinstance(tolerance, (int, float)) or not 1 <= tolerance <= 100:
                raise ValueError("Colour tolerance must be between 1 and 100 Delta E.")
        if self.rule_type == "typography" and not (isinstance(value.get("value"), str) and value["value"].strip()):
            raise ValueError("Typography rules require a non-empty descriptive value.")
        return self


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_type: str
    parameters: dict[str, Any]
    channel: str | None
    valid_from: date | None
    valid_to: date | None
    source_passage_id: str | None
    status: str
    created_by: str
    created_at: datetime


class RuleDecision(StrictInput):
    decision: Literal["approve", "reject"]
    note: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=1000)] = None
