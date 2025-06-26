# Interactive Form Helpers

This directory contains reusable utilities for interactive form processing.

## InteractiveSession

`InteractiveSession` is a utility class that encapsulates all the functionality needed to run interactive form-filling sessions with LLM-powered agents. It provides a standardized interface for managing interactive sessions across different form models.

### Features

- Consistent console-based UI for user interactions
- Progress tracking with visual progress bars
- Detailed JSON output of form state
- Customizable callback when form is completed
- Standardized error handling and logging
- Support for any form model based on `BaseFormModel`

### Usage Example

```python
import asyncio
from pydantic import Field
from pydantic3.agents import BaseFormModel
from pydantic3.agents.examples.helpers import InteractiveSession

# Define your form model
class MyForm(BaseFormModel):
    name: str = Field(default="", description="Name")
    age: int = Field(default=0, description="Age in years")

# Optional callback when form is completed
async def on_form_complete(form_data):
    print(f"Form completed for user: {form_data.session_info.user_form.name}")

async def main():
    # Method 1: Using the class method (simplest approach)
    await InteractiveSession.run_with_form(
        form_class=MyForm,
        role_prompt="Be concise and friendly.",
        completion_threshold=80,
        on_form_completion=on_form_complete
    )

    # Method 2: Creating an instance for more control
    session = InteractiveSession(
        form_class=MyForm,
        role_prompt="Be concise and friendly.",
        completion_threshold=80,
        verbose=True,
        logger_name="my_app.forms"
    )

    # Run the complete interactive session
    await session.run_interactive_session()

    # Or run it step by step for more control
    if session.setup():
        await session.initialize_session()
        user_input = session.get_user_input("Type something: ")
        response = await session.process_user_message(user_input)
        # Process response...

if __name__ == "__main__":
    asyncio.run(main())
```

### Configuration Options

- `form_class`: The Pydantic model class for your form
- `api_key_env_var`: Name of environment variable containing the API key (default: "OPENROUTER_API_KEY")
- `model_name`: LLM model to use (default: "openai/gpt-4o-2024-11-20")
- `role_prompt`: Custom instructions for the agent
- `completion_threshold`: Progress threshold to consider form complete (0-100)
- `verbose`: Enable detailed logging
- `logger_name`: Name for the logger
- `on_form_completion`: Callback function when form reaches completion

### Requirements

- Environment variable with API key must be set
- Dependencies: pydantic, questionary
