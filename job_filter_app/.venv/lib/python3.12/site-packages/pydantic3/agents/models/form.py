"""Form data models."""

from .analytics import AnalyticsResult
from typing import Dict, Any, Type, Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer, create_model
import json
import traceback

from ...utils import SimpleLogger

logger = SimpleLogger("models.form")


class BaseFormModel(BaseModel):
    """Base class for defining the structure of a specific form."""
    model_config = ConfigDict(validate_assignment=True)


class MessageHistory(BaseModel):
    id: int = Field(description="Unique identifier for the message")
    role: str = Field(description="Role of the message sender")
    content: str = Field(description="Content of the message")
    created_at: str = Field(description="Timestamp of the message creation")
    session_id: str = Field(description="Session ID of the message")
    language: str = Field(default="en", description="Language of the message content")


class UserInfo(BaseModel):
    """User information."""
    name: str = Field(description="Name of the user")


class FormMetadata(BaseModel):
    """Metadata associated with the form processing state."""
    previous_question: str = Field(default="", description="Previous question to ask the user")
    next_message_ai: str = Field(default="", description="Next question to ask the user")
    next_message_language: str = Field(default="en", description="Language of the next question")
    progress: int = Field(default=0, description="Form completion progress (0-100)")
    user_info: Optional[UserInfo] = Field(default=None, description="User information")
    user_language: str = Field(default="en", description="Detected user language")
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        coerce_numbers_to_str=False
    )

    @classmethod
    def model_validate(cls, obj: Any, **kwargs) -> "FormMetadata":
        """Override model_validate to handle potential float progress values from LLM."""
        if isinstance(obj, dict) and "progress" in obj and isinstance(obj["progress"], float):
            logger.warning(f"Received float progress '{obj['progress']}', converting to int.")
            obj = obj.copy()
            obj["progress"] = int(obj["progress"])
        return super().model_validate(obj, **kwargs)

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v) -> int:
        """Ensure progress is an integer between 0 and 100."""
        if isinstance(v, float):
            logger.warning(f"Progress validator received float '{v}', converting to int.")
            v = int(v)
        if not 0 <= v <= 100:
            logger.warning(f"Progress {v} out of range (0-100), clamping.")
            v = max(0, min(v, 100))
        return v


class System(BaseModel):
    """System configuration for the form processing, including session and model parameters."""
    # Core settings
    completion_threshold: int = 100
    completion_achieved: bool = False

    # Added context fields
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    client_id: Optional[str] = Field(default=None, description="Client application identifier")
    role_prompt: Optional[str] = Field(default=None, description="LLM role definition prompt")
    model_name: Optional[str] = Field(default=None, description="LLM model name used for the session")
    temperature: Optional[float] = Field(default=None, description="LLM temperature setting")
    form_defaults: Optional[Dict[str, Any]] = Field(default=None, description="Default values of the form model fields")

    model_config = ConfigDict(validate_assignment=True)


class SessionInfo(BaseModel):
    """Container holding both the form data and associated metadata."""
    user_form: BaseModel
    metadata: FormMetadata = Field(default_factory=FormMetadata)

    @field_serializer('user_form')
    def serialize_user_form(self, v: BaseModel):
        """Ensure proper serialization of user_form"""
        if hasattr(v, "model_dump"):
            return v.model_dump(mode="json")
        return v


class FormData(BaseModel):
    """
    Container for form data and metadata.

    This class holds both the actual form model instance (inheriting from BaseFormModel)
    and associated metadata about the form completion status, conversation history,
    system configuration, and analytics results.
    """
    session_info: SessionInfo
    system: System = Field(default_factory=System)
    history: List[MessageHistory] = Field(default_factory=list, description="Conversation history")
    analytics: Optional[AnalyticsResult] = Field(default=None, description="Analytics results of the form")

    def update_progress(self, new_progress: int):
        """Updates the progress and recalculates the completion status based on the threshold."""
        old_progress = self.session_info.metadata.progress
        self.session_info.metadata.progress = max(0, min(new_progress, 100))
        old_completion_status = self.system.completion_achieved
        self.system.completion_achieved = self.session_info.metadata.progress >= self.system.completion_threshold
        if old_progress != self.session_info.metadata.progress:
            logger.info(f"Progress updated: {old_progress}% -> {self.session_info.metadata.progress}%")
        if old_completion_status != self.system.completion_achieved:
            logger.info(f"Completion status changed: {old_completion_status} -> {self.system.completion_achieved}")

    def update_form(self, form_data):
        """Updates the form data with new values from dictionary or model.

        Args:
            form_data: Dictionary with form data or BaseModel instance
        """
        logger.info(f"Updating form with new data: {type(form_data)}")

        try:
            if isinstance(form_data, dict):
                # Get the current form class to maintain the correct type
                current_form_class = self.session_info.user_form.__class__
                logger.info(f"Creating new {current_form_class.__name__} instance from dict")
                # Create a new instance with the updated data
                new_form = current_form_class.model_validate(form_data)
                # Update the form
                self.session_info.user_form = new_form
                logger.info(f"Form updated successfully from dictionary: {json.dumps(form_data, indent=2, ensure_ascii=False)}")
            elif isinstance(form_data, BaseModel):
                # Direct assignment if it's already a model
                self.session_info.user_form = form_data
                logger.info("Form updated successfully from model")
            else:
                logger.error(f"Cannot update form with data of type: {type(form_data)}")
        except Exception as e:
            logger.error(f"Error updating form: {e}")
            logger.error(traceback.format_exc())

    @classmethod
    def create_empty(cls, form_class: Type[BaseFormModel]) -> "FormData":
        """Creates an empty FormData instance for a given form class."""
        logger.info(f"Creating empty FormData for {form_class.__name__}")
        session_info = SessionInfo(user_form=form_class())
        return cls(session_info=session_info)

    def safe_dict(self) -> Dict[str, Any]:
        """Converts the FormData object to a dictionary suitable for serialization."""

        # Prepare metadata dictionary
        metadata_dict = {}
        if hasattr(self.session_info, 'metadata') and self.session_info.metadata is not None:
            try:
                # Use mode="json" for proper serialization of nested models
                metadata_dict = self.session_info.metadata.model_dump(mode="json")
            except Exception as e:
                logger.error(f"safe_dict: Error converting metadata to dict: {e}")

        system_dict = {}
        if hasattr(self, 'system') and self.system is not None:
            try:
                # Use mode="json" for proper serialization of nested models
                system_dict = self.system.model_dump(mode="json")
            except Exception as e:
                logger.error(f"safe_dict: Error converting system to dict: {e}")

        # Prepare analytics dictionary, if present
        analytics_dict = None
        if hasattr(self, 'analytics') and self.analytics is not None:
            try:
                # Use mode="json" for proper serialization of nested models
                analytics_dict = self.analytics.model_dump(mode="json")
            except Exception as e:
                logger.error(f"safe_dict: Error converting analytics to dict: {e}")

        user_form_dict = {}
        if hasattr(self.session_info, 'user_form') and self.session_info.user_form is not None:
            try:
                # Handle both dict and model cases
                if isinstance(self.session_info.user_form, dict):
                    user_form_dict = self.session_info.user_form
                else:
                    # Ключевое изменение: сохраняем все поля, включая пустые, и исключаем None-значения
                    user_form_dict = self.session_info.user_form.model_dump(
                        mode="json",
                        exclude_none=False,        # Сохраняем None-значения
                        exclude_defaults=False,    # Сохраняем значения по умолчанию
                        exclude_unset=False        # Сохраняем неустановленные значения
                    )
                logger.info(f"safe_dict: Form data serialized: {json.dumps(user_form_dict, indent=2, ensure_ascii=False)}")
            except Exception as e:
                logger.error(f"safe_dict: Error converting user_form to dict: {e}")
                logger.error(traceback.format_exc())

        # Create the final dictionary
        data = {
            "user_form": user_form_dict,
            "metadata": metadata_dict,
            "system": system_dict,
            "analytics": analytics_dict
        }

        return data


def create_form_model(name: str, fields: Dict[str, Any]) -> Type[BaseFormModel]:
    """Dynamically creates a Pydantic model inheriting from BaseFormModel."""
    logger.info(f"Dynamically creating form model '{name}'")
    return create_model(name, __base__=BaseFormModel, **fields)
