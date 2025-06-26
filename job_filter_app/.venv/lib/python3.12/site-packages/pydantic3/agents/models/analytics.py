"""Analytics models for form processing."""

# import logging # Removed unused import
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator
from ...utils import SimpleLogger

# Configure logging using the utility
logger = SimpleLogger("models.analytics")


class AnalyticsUser(BaseModel):
    """User profile and interaction analysis based on the session."""
    communication_style: Optional[str] = Field(default=None, description="Identified communication style (e.g., formal, informal, concise, verbose)")
    sentiment: Optional[str] = Field(default=None, description="Overall sentiment detected (e.g., positive, neutral, negative)")
    engagement_level: Optional[str] = Field(default=None, description="Level of user engagement (e.g., high, medium, low, cooperative, hesitant)")
    key_topics_mentioned: List[str] = Field(default_factory=list, description="Key topics or keywords frequently mentioned by the user")
    potential_traits: List[str] = Field(default_factory=list, description="Observed potential personality traits (e.g., detail-oriented, decisive, cautious)")


class AnalyticsResult(BaseModel):
    """
    Strictly universal analysis of data quality and user interaction patterns.

    Focuses ONLY on assessing the characteristics of the submitted data
    (completeness, clarity, consistency) and the user's interaction style,
    irrespective of the 'user_form''s semantic content or purpose.
    """
    # Core Fields retained/modified:
    user: AnalyticsUser = Field(..., description="Analysis of the user's interaction patterns based on history")
    score: Optional[int] = Field(default=None, description="Overall data quality score (0-10) based ONLY on completeness, clarity, and consistency")
    data_quality: int = Field(default=..., description="Overall data quality score (0-10) based ONLY on completeness, clarity, and consistency")
    data_summary: Optional[str] = Field(default=None, description="Objective summary of data structure and content patterns")
    data_observations: List[str] = Field(default_factory=list, description="Objective observations about the data itself (e.g., 'field_x frequently empty', 'field_y uses inconsistent date 'user_form'ats')")
    identified_data_issues: List[str] = Field(default_factory=list, description="Specific data points or fields identified with issues (contradictions, 'user_form'at errors, ambiguities)")
    clarification_prompts: List[str] = Field(default_factory=list, description="Suggested prompts to ask the user to clarify specific data issues identified")

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: Optional[int]) -> Optional[int]:
        """Validate that the score is between 0 and 10."""
        if v is not None and not 0 <= v <= 10:
            logger.warning(f"Score out of range (0-10): {v}, clamping to valid range")  # Log warning
            return max(0, min(v, 10))
        return v

    @classmethod
    def create_empty(cls) -> "AnalyticsResult":
        """Creates an empty AnalyticsResult instance with default messages."""
        logger.info("Creating empty AnalyticsResult focused on data quality.")  # Log info
        return cls(
            user=AnalyticsUser(),  # Provide default empty user analysis
            data_quality={"status": "No data assessed yet"},
            data_summary="No data submitted for summary.",
            identified_data_issues=["'user_form' not yet analyzed for data issues."],
            clarification_prompts=["Complete the 'user_form' for data quality analysis."]
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalyticsResult":
        """Creates an instance from a dictionary, ensuring essential fields exist."""
        # Ensure user field is present or provide default
        if "user" not in data:
            logger.warning("'user' field missing in data for AnalyticsResult.from_dict, adding default.")  # Log warning
            data["user"] = AnalyticsUser().model_dump()
        elif not isinstance(data["user"], dict):
            logger.warning("'user' field is not a dict, attempting default.")
            data["user"] = AnalyticsUser().model_dump()

        # Ensure data_quality field is present or provide default
        if "data_quality" not in data:
            logger.warning("'data_quality' field missing in data for AnalyticsResult.from_dict, adding default.")  # Log warning
            data["data_quality"] = {"status": "Analysis did not provide data quality details."}
        elif not isinstance(data["data_quality"], dict):
            logger.warning("'data_quality' field is not a dict, attempting default.")
            data["data_quality"] = {"status": "Analysis provided invalid data quality 'user_form'at."}

        # Create instance
        try:
            # Filter data to only include fields defined in the model
            # This prevents errors if the LLM includes extra fields (like the old ones)
            defined_fields = cls.model_fields.keys()
            filtered_data = {k: v for k, v in data.items() if k in defined_fields}

            instance = cls(**filtered_data)
            logger.info("Successfully created AnalyticsResult (Data Quality Focus) from dict.")  # Log info
            return instance
        except Exception as e:
            logger.error(f"Error creating strict AnalyticsResult from dict: {e}")  # Log error
            logger.warning("Returning empty strict AnalyticsResult due to creation error.")  # Log warning
            return cls.create_empty()
