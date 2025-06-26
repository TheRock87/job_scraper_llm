"""Example of using the InteractiveSession helper with a FormIntentRequest form."""

import asyncio

from pydantic3.agents.helpers import InteractiveSession
from pydantic3.agents.wizards.form.settings import Settings
from pydantic3.agents.wizards.form.models import SetupRequest


async def main():
    """Run the interactive form example."""
    # Role prompt defines the AI's personality

    # Run the interactive session with our form
    await InteractiveSession.run_with_form(
        form_class=SetupRequest,
        role_prompt=Settings.role_prompt,
        completion_threshold=Settings.completion_threshold,
        model_name=Settings.model_name,
        logger_name="examples.form_intent",
        verbose=False,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted. Shutting down.")
