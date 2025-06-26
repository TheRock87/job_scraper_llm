"""Example of using the InteractiveSession helper with a simple user profile form."""

import asyncio
from typing import List
from pydantic import Field

from pydantic3.agents import BaseFormModel
from pydantic3.agents.helpers import InteractiveSession


class Preferences(BaseFormModel):
    """User preferences information."""
    favorite_color: str = Field(default="", description="Favorite color")
    favorite_foods: List[str] = Field(default_factory=list, description="List of favorite foods")
    likes_travel: bool = Field(default=False, description="Whether the user enjoys traveling")


class UserProfileForm(BaseFormModel):
    """Simple user profile form."""
    name: str = Field(default="", description="User's full name")
    age: int = Field(default=0, description="User's age in years")
    bio: str = Field(default="", description="Short biography")
    occupation: str = Field(default="", description="Current job or occupation")
    preferences: Preferences = Field(default_factory=Preferences, description="User preferences")


async def main():
    """Run the interactive form example."""
    # Role prompt defines the AI's personality
    role_prompt = """
    Be friendly and conversational.
    Ask follow-up questions about the user's answers.
    Occasionally add a gentle joke or humorous comment.
    """

    # Run the interactive session with our form
    await InteractiveSession.run_with_form(
        form_class=UserProfileForm,
        role_prompt=role_prompt,
        completion_threshold=80,  # Form will be considered complete at 80%
        model_name="openai/gpt-4o-mini-2024-07-18",  # Use a smaller model for testing
        logger_name="examples.simple_interactive",
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted. Shutting down.")
