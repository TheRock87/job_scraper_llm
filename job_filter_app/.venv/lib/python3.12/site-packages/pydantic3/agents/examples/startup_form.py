"""Example usage of the form processing framework with a startup form."""

import asyncio
import os
from typing import List
from datetime import datetime

from pydantic import Field
from pydantic3.agents import FormProcessor, BaseFormModel
from pydantic3.utils import SimpleLogger, LogConsole


# Create a logger using our SimpleLogger class
logger = SimpleLogger("examples.startup_form")

console = LogConsole(
    name="examples.startup_form"
)


class StartupForm(BaseFormModel):
    """Form for collecting startup information."""
    name: str = Field(default="", description="Startup name")
    industry: str = Field(default="", description="Industry or sector")
    description: str = Field(default="", description="Brief description of the product/service")
    problem_statement: str = Field(default="", description="Problem the startup is solving")
    target_market: str = Field(default="", description="Target customer segments")
    business_model: str = Field(default="", description="How the startup makes money")
    competitors: List[str] = Field(default_factory=list, description="Main competitors")
    team_size: int = Field(default=0, description="Number of team members")
    funding_needed: float = Field(default=0.0, description="Funding amount needed in USD")
    funding_stage: str = Field(default="", description="Current funding stage (e.g., seed, Series A)")
    traction: str = Field(default="", description="Current traction metrics")
    location: str = Field(default="", description="Primary location/HQ")
    founding_year: int = Field(default=0, description="Year the startup was founded")


async def process_startup_form():
    """Example function for processing a startup form."""
    # Create a session ID for contextual logging
    session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    ctx_logger = logger.bind(session_id=session_id)

    # Get API key from environment
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        ctx_logger.error("OPENROUTER_API_KEY environment variable not set")
        return

    # Initialize processor
    ctx_logger.info("Initializing FormProcessor...")
    processor = FormProcessor(
        form_class=StartupForm,
        api_key=api_key,
        model_name="openai/gpt-4o-2024-11-20-mini",
        completion_threshold=30,  # Set lower threshold to trigger analytics
        role_prompt="Talk to the user in Russian.",
        verbose=False
    )

    try:
        # Start a new session
        processor_session_id = await processor.start_session("example_user")
        # Add processor session ID to logger context
        ctx_logger = ctx_logger.bind(processor_session_id=processor_session_id)
        ctx_logger.success("Successfully started processor session")

        # Sample conversations
        messages_en = [
            "Hi, I want to tell you about my startup called TechWave.",
            "We're building an AI-powered analytics platform for e-commerce businesses.",
            "We're targeting small to medium-sized online retailers who struggle with data analysis.",
            "We have 5 team members, all with background in ML and e-commerce.",
            # "We're based in San Francisco and looking for $500,000 in seed funding.",
            # "Our main competitors are Shopify Analytics, but our solution is more affordable and easier to use.",
            # "We charge a monthly subscription fee based on store size, starting at $99/month.",
            # "We already have 10 paying customers and have been growing 20% month over month.",
            # "We started in 2022 and have been bootstrapped so far."
        ]

        # Russian version of the example (commented out)
        # messages_ru = [
        #     "Привет, я хочу рассказать вам о своем стартапе под названием TechWave.",
        #     "Мы строим платформу аналитики на основе ИИ для интернет-магазинов.",
        #     "Целевая аудитория - малые и средние интернет-магазины, которые испытывают трудности с анализом данных.",
        #     "У нас 5 членов команды, все из них имеют образование в области машинного обучения и электронной коммерции.",
        #     "Мы находимся в Сан-Франциско и ищем $500,000 в качестве стартового капитала.",
        # ]

        # Process messages
        for i, msg in enumerate(messages_en):
            ctx_logger.info(f"Processing message [{i+1}/{len(messages_en)}]: {msg}")
            response = await processor.process_message(msg, processor_session_id)

            if response.system.completion_achieved and response.analytics:
                ctx_logger.success("Form is complete!")
                # Log form data using log_json method
                console.print_json(message="Final form data", data=response.model_dump())
                break

            # Log current form state with JSON formatting
            console.print_json(message="Current form data", data=response.session_info.user_form.model_dump())

            # Wait a moment before next message to avoid overwhelming output
            await asyncio.sleep(0.5)

    except Exception:
        # Use automatic traceback with rich formatting
        ctx_logger.exception("Unexpected error during form processing")


if __name__ == "__main__":
    logger.info("Starting startup form processing example")
    asyncio.run(process_startup_form())
    logger.info("Example completed")
