"""Simple test script for FormGenerator."""

import os
import asyncio
from pathlib import Path
from pydantic import ValidationError
from pydantic3.agents.wizards.form.form_generator import FormGenerator
from pydantic3.agents.wizards.form.models import SetupRequest
from pydantic3.utils import LogConsole, SimpleLogger
import questionary


logger = SimpleLogger('examples.form_generator_test')
console = LogConsole('examples.form_generator_test')

# Test data for form generation
SETUP_DATA = {
  "info": {
    "description": "A platform for automating customer feedback collection through AI-powered forms.",
    "industry": "SaaS",
    "type": "b2b",
    "goals": [
      "Improve customer satisfaction tracking",
      "Automate feedback analysis",
      "Enhance user onboarding"
    ],
    "website": "https://example.com",
    "customers_language": "en"
  },
  "settings": {
    "model_tier": "high",
    "bot_name": "Formie",
    "completion_threshold": 90,
    "bot_style": "friendly",
    "use_emojis": True,
    "simulate_delay": True,
    "welcome_message": "Hi there! I'm here to help you fill out this quick form 📝",
    "completion_message": "Thanks for completing the form! We'll be in touch soon. 🎉"
  }
}


# Save directory path
SAVE_DIR = "/Users/markinmatrix/Documents/htdocs/@REFORMS/pydantic3/src/pydantic3/agents/examples/saved"

# Available languages
LANGUAGES = {
    "English": "en",
    "Russian": "ru",
    "Spanish": "es",
    "French": "fr"
}

# test validation
try:
    setup_request = SetupRequest(**SETUP_DATA)
    print("✅ Validation passed")
    print(setup_request)
except ValidationError as e:
    print(f"❌ Validation error: {e}")
    import traceback
    traceback.print_exc()


async def test_form_generator(language: str):
    """Test FormGenerator with single-request form generation."""
    # Get API key from environment
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("❌ OPENROUTER_API_KEY environment variable not set")
        return

    logger.info(f"🧪 Starting FormGenerator test with language: {language}")
    logger.info("🔄 Creating FormGenerator...")
    generator = FormGenerator(
        setup_data=SETUP_DATA,
        api_key=api_key,
        language=language
    )

    try:
        # Generate complete structure in a single request
        logger.info("\n🔄 Generating complete form structure...")
        complete_structure = await generator.generate_complete_structure()

        # Print the results
        logger.info("\n✅ Generated complete structure:")
        logger.info(f"Document: {complete_structure.document.title}")
        logger.info(f"Forms count: {len(complete_structure.forms)}")

        console.print_json('Generated complete structure:', complete_structure.model_dump())

        # Ensure the save directory exists
        save_dir = Path(SAVE_DIR)
        save_dir.mkdir(exist_ok=True, parents=True)

        # Save the result to a JSON file
        save_path = save_dir / f"form_structure_{language}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(complete_structure.model_dump_json(indent=2))
        logger.info(f"\n✅ Saved complete structure to {save_path}")

        return complete_structure

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Interactive language selection with questionary
    logger.info("📋 Form Generator Test")
    logger.info("=====================")

    # Ask user to select a language using questionary
    selected_language = questionary.select(
        "Select language for form generation:",
        choices=list(LANGUAGES.keys()),
        use_indicator=True,
        style=questionary.Style([
            ('qmark', 'fg:green bold'),
            ('question', 'bold'),
            ('selected', 'fg:cyan bold'),
        ])
    ).ask()

    # Get the language code from the selection
    language_code = LANGUAGES.get(selected_language, "en")

    # Run the test with the selected language
    result = asyncio.run(test_form_generator(language=language_code))

    if result:
        logger.info("\n✅ Test completed successfully")
    else:
        logger.error("\n❌ Test failed")
