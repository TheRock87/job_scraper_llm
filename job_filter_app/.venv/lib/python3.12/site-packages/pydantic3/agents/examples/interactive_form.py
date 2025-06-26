"""Interactive example of the form processing framework with user input via console."""

import asyncio
from typing import List
from pydantic import BaseModel, Field

from pydantic3.agents import BaseFormModel
from pydantic3.agents.helpers import InteractiveSession


# Create nested 3rd level models
class ContactInfo(BaseModel):
    """Contact information."""
    email: str = Field(default="", description="Email contact")
    phone: str = Field(default="", description="Phone number")
    website: str = Field(default="", description="Website")


class MarketInfo(BaseModel):
    """Market information."""
    size: str = Field(default="", description="Market size")
    growth_rate: float = Field(default=0.0, description="Market growth rate in %")
    competitors: List[str] = Field(default_factory=list, description="List of competitors")


class StartupForm(BaseFormModel):
    """Form for collecting startup information."""
    name: str = Field(default="", description="Startup name")
    description: str = Field(default="", description="Product/service description")
    industry: str = Field(default="", description="Industry/sector")
    problem_statement: str = Field(default="", description="Problem that the startup solves")
    market: MarketInfo = Field(default_factory=MarketInfo, description="Market information")
    contact: ContactInfo = Field(default_factory=ContactInfo, description="Contact information")


async def main():
    """Run the interactive form example with a startup form."""
    # Configure the role prompt
    role_prompt = """
    Speak with the user in their language and be concise.
    Ask specific questions about the startup.
    Be sarcastic and communicate in Pelevin's style.
    Dive deep into the problem the startup is solving and its market potential.
    """

    # Run the interactive session with our form
    await InteractiveSession.run_with_form(
        form_class=StartupForm,
        role_prompt=role_prompt,
        completion_threshold=80,  # Form is considered complete at 80%
        model_name="openai/gpt-4o-2024-11-20",
        logger_name="examples.interactive_form",
        verbose=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted. Shutting down.")
