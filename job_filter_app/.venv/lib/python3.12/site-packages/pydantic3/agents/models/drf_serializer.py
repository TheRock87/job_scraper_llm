from drf_pydantic import BaseModel as DRFBaseModel
from pydantic import Field, BaseModel
from typing import List, Optional

from .form import MessageHistory, UserInfo
from .analytics import AnalyticsResult


class Pyndatic3FormMetadata(BaseModel):
    """Base class for defining the structure of a specific form."""
    next_message_ai: str = ""
    next_message_language: str = "en"
    progress: int = 0
    user_info: Optional[UserInfo] = None
    user_language: str = "en"


class Pyndatic3SessionInfo(DRFBaseModel):
    """Base class for defining the structure of a specific form."""
    metadata: Pyndatic3FormMetadata = Field(default_factory=Pyndatic3FormMetadata)
    user_form: str = Field(default="{}", description="JSON string representation of form data")


class Pyndatic3System(BaseModel):
    """Base class for defining the structure of a specific form."""
    completion_threshold: int = Field(default=100)
    completion_achieved: bool = Field(default=False)
    session_id: Optional[str] = None
    client_id: Optional[str] = None
    role_prompt: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    form_defaults: str = Field(default="{}", description="JSON string representation of form defaults")


class Pyndatic3AgentResponse(DRFBaseModel):
    """Base class for defining the structure of a specific form."""
    session_info: Pyndatic3SessionInfo = Field(default_factory=Pyndatic3SessionInfo)
    system: Pyndatic3System = Field(default_factory=Pyndatic3System)
    analytics: Optional[AnalyticsResult] = None
    history: Optional[List[MessageHistory]] = Field(default_factory=list)
