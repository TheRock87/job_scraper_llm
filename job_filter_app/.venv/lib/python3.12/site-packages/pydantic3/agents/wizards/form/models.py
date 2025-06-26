"""Form wizard models."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl
from drf_pydantic import BaseModel as DRFBaseModel


class Info(BaseModel):
    description: str = Field(..., description="Brief description of your business or product")
    # industry: str = Field(..., description="Industry (e.g. Healthcare, Fintech)")
    # website: Optional[HttpUrl] = Field(
    #     None,
    #     description="Website URL of the business"
    # )
    type: Literal["b2b", "b2c", "internal", "custom"] = Field(
        ...,
        description="Type of customer interaction (b2b, b2c, internal use, or custom)"
    )
    goals: List[str] = Field(
        ...,
        min_items=1,
        max_items=3,
        description="Main goals of the business related to the form (1 to 3 items)"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes about the business or product"
    )


class Settings(BaseModel):
    # model_tier: Literal["low", "medium", "high"] = Field(
    #     "medium",
    #     description="AI model tier used to process and analyze the form (low = basic, high = advanced)"
    # )
    # model_temperature: float = Field(
    #     0.5,
    #     ge=0.0,
    #     le=1.0,
    #     description="Temperature of the AI model"
    # )
    bot_name: Optional[str] = Field(
        None,
        description="Name of the assistant bot"
    )
    # completion_threshold: int = Field(
    #     100,
    #     ge=50,
    #     le=100,
    #     description="Form is considered completed when this percentage is reached (50–100)"
    # )
    bot_style: Optional[str] = Field(
        "friendly",
        description="Bot's communication style (e.g. formal, friendly, casual)"
    )
    # use_emojis: bool = Field(
    #     True,
    #     description="Whether the bot is allowed to use emojis in its messages"
    # )
    # simulate_delay: bool = Field(
    #     True,
    #     description="Whether the bot should simulate a typing delay before responding"
    # )
    welcome_message: Optional[str] = Field(
        None,
        description="Text shown to users before they start filling out the form"
    )
    completion_message: Optional[str] = Field(
        None,
        description="Text shown to users after they complete the form"
    )
    customers_language: Optional[str] = Field(
        None,
        description="Language of the customer (ISO 639-1 code). Can be multiple languages (comma separated)."
    )
    # ui_language: str = Field(
    #     None,
    #     description="Language of the interface (ISO 639-1 code). Only one language is supported."
    # )


class SetupRequest(DRFBaseModel):
    info: Info = Field(default_factory=dict, description="Business information")
    settings: Settings = Field(default_factory=dict, description="Bot settings")
