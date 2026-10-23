from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class JobState(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class Captions(BaseModel):
    burn_in: bool = True
    srt: bool = True


class SceneInput(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    visual_hint: str | None = Field(default=None, max_length=1000)


class CreateJobRequest(BaseModel):
    audio_url: HttpUrl | None = None
    script: str | None = Field(default=None, max_length=30000)
    scenes: list[SceneInput] | None = Field(default=None, max_length=100)
    voice: str = Field(default="en-IN-female", max_length=100)
    aspect_ratios: list[Literal["16:9", "9:16", "1:1"]] = Field(default_factory=lambda: ["16:9"])
    style: str = Field(default="bright, modern, real-world footage", max_length=500)
    avoid: list[str] = Field(default_factory=list, max_length=30)
    captions: Captions = Field(default_factory=Captions)
    callback_url: HttpUrl | None = None

    @model_validator(mode="after")
    def exactly_one_input(self) -> "CreateJobRequest":
        values = [self.audio_url is not None, bool((self.script or "").strip()), bool(self.scenes)]
        if sum(values) != 1:
            raise ValueError("Provide exactly one of audio_url, non-empty script, or scenes")
        if self.script is not None and not self.script.strip():
            raise ValueError("script must not be empty")
        if len(set(self.aspect_ratios)) != len(self.aspect_ratios):
            raise ValueError("aspect_ratios must not contain duplicates")
        return self


class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody


class JobAccepted(BaseModel):
    job_id: str
    status: JobState
    reused: bool = False


class JobStatus(BaseModel):
    job_id: str
    status: JobState
    progress: int = Field(ge=0, le=100)
    error: ErrorBody | None = None
    result_links: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class SwapClipRequest(BaseModel):
    scene_id: str = Field(min_length=1, max_length=50)
    new_query: str | None = Field(default=None, max_length=500)
    new_asset_url: str | None = Field(default=None, max_length=2000)


class SwapClipResponse(BaseModel):
    job_id: str
    scene_id: str
    swapped_clip: dict
    re_render_seconds: float
    result_links: dict[str, str]

