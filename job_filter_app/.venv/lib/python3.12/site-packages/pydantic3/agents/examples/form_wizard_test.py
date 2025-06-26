"""Example that tests the FormWizard functionality."""

import os
import asyncio
from typing import Optional, Dict, Any

from pydantic3.agents.wizards.form import FormWizard
from pydantic3.utils import LogConsole, SimpleLogger
from pydantic3.agents.wizards.form.form_generator import FormGenerator, CompleteFormStructure


# Logging setup
logger = SimpleLogger("examples.form_wizard_test")
console = LogConsole(name="examples.form_wizard_test")


async def test_form_generation(setup_data: Dict[str, Any]) -> Optional[CompleteFormStructure]:
    """Test form structure generation from collected data."""
    logger.info("Testing form structure generation")

    # Get API key from environment
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY environment variable not set")
        return

    # Create generator
    generator = FormGenerator(
        setup_data=setup_data,
        api_key=api_key
    )

    try:
        # Generate complete structure in parallel
        logger.info("Generating complete form structure...")
        complete_structure = await generator.generate_complete_structure()

        # Show the results
        logger.success("Form structure generated successfully")
        console.print_json(message="Generated form structure", data=complete_structure.model_dump(mode="json"))

        return complete_structure
    except Exception as e:
        logger.error(f"Error generating form structure: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


async def test_basic_flow() -> None:
    """Test the basic form flow with the wizard."""
    logger.info("Testing basic form wizard flow")

    # Get API key from environment
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY environment variable not set")
        return

    # Create wizard instance
    wizard = FormWizard(api_key=api_key, verbose=True)
    logger.success(f"Created wizard with model: {wizard.model_name}")

    # Start session
    session_id = await wizard.start_session("test_user")
    logger.success(f"Started session: {session_id}")

    # Get initial state
    form_data = await wizard.get_form_state()
    logger.info("Got initial form state")
    logger.info(f"Initial message: {form_data.session_info.metadata.next_message_ai}")

    # Print initial form data
    console.print_json(message="Initial form data", data=form_data.safe_dict())

    # Test a series of messages
    test_messages = [
        "I'm creating a feedback form for an online store",
        "Our business sells handmade crafts and art supplies",
        "The form will be filled out by customers after they make a purchase",
        "We need to ask about product quality, delivery speed, and overall satisfaction",
        "We want to use a friendly communication style with emojis"
    ]

    # Process each message
    for idx, message in enumerate(test_messages, 1):
        logger.info(f"Processing message [{idx}/{len(test_messages)}]: '{message}'")

        # Process the message
        response = await wizard.process_message(message)

        # Show progress
        progress = response.session_info.metadata.progress
        logger.info(f"Form completion: {progress}%")

        # Show AI response
        logger.info(f"AI response: {response.session_info.metadata.next_message_ai}")

        # Show updated form data
        console.print_json(message=f"Form data after message {idx}", data=response.safe_dict())

    # Get message history
    messages = await wizard.get_message_history()
    logger.info(f"Retrieved {len(messages)} messages from history")

    # Try direct processor method access
    session_info = await wizard.processor_instance.session_manager.get_session_info(session_id)
    logger.info(f"Accessed processor directly: session created at {session_info.get('created_at', 'unknown')}")

    # Test __getattr__ method for direct access to processor methods
    try:
        # Use session_manager directly, which definitely exists
        latest_state = await wizard.processor_instance.session_manager.get_latest_form_data(session_id)
        logger.success("Accessed processor method via session_manager")
        if latest_state:
            logger.info(f"Form data contains {len(latest_state)} fields")
    except Exception as e:
        logger.error(f"Error accessing processor method: {e}")

    # Get the final form state and print detailed information
    final_form = await wizard.get_form_state()
    form_dict = final_form.safe_dict()
    user_form = form_dict.get("user_form", {})
    system_data = form_dict.get("system", {})

    logger.info("FINAL FORM FIELDS SUMMARY:")
    for key, value in user_form.items():
        if isinstance(value, dict):
            logger.info(f"{key.upper()}:")
            for sub_key, sub_value in value.items():
                logger.info(f"  - {sub_key}: {sub_value}")
        else:
            logger.info(f"{key.upper()}: {value}")

    # Print full data structure for analysis
    console.print_json(message="Full form data structure", data=form_dict)

    # General form information from metadata
    logger.info(f"Form completion status: {final_form.session_info.metadata.progress}%")
    logger.info(f"User language: {final_form.session_info.metadata.user_language}")

    # Get completion_threshold information from system, if available
    completion_threshold = system_data.get("completion_threshold", 90)
    completion_achieved = system_data.get("completion_achieved", False)
    logger.info(f"Completion threshold: {completion_threshold}%")
    logger.info(f"Achievement status: {'Completed' if completion_achieved else 'In Progress'}")
    logger.info(f"Progress: {progress}%")

    # Test form structure generation if the form is filled sufficiently
    if progress >= 50:  # Using a reduced threshold for demonstration
        logger.info("Form is sufficiently completed. Testing form structure generation...")
        await test_form_generation(user_form)

    logger.success("All tests complete")


async def main():
    """Run all tests."""
    await test_basic_flow()


if __name__ == "__main__":
    asyncio.run(main())
    logger.info("Tests finished")
