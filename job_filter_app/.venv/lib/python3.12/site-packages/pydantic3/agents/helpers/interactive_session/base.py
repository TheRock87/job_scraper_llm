"""Interactive session utility for form processing."""

import os
import asyncio
import json
from typing import Type, Optional
from datetime import datetime

from ...core.processor import FormProcessor
from ...models.form import FormData, BaseFormModel
from ....utils import SimpleLogger, LogConsole


def create_progress_bar(percentage: int, width: int = 20) -> str:
    """Create a text-based progress bar."""
    filled_width = int(width * percentage / 100)
    bar = "█" * filled_width + "░" * (width - filled_width)
    return f"{bar} {percentage}%"


def _sync_get_input(prompt: str) -> str:
    """Get user input synchronously."""
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        return "exit"


class InteractiveSession:
    """Reusable class to handle interactive form sessions with any form model."""

    def __init__(
        self,
        form_class: Type[BaseFormModel],
        api_key_env_var: str = "OPENROUTER_API_KEY",
        model_name: str = "openai/gpt-4o-2024-11-20",
        role_prompt: str = "",
        completion_threshold: int = 100,
        verbose: bool = True,
        logger_name: str = "examples.interactive"
    ):
        """
        Initialize an interactive form session.

        Args:
            form_class: The form model class to use
            api_key_env_var: Environment variable name containing the API key
            model_name: The LLM model to use
            role_prompt: Custom instructions for the LLM
            completion_threshold: Threshold to consider the form complete (0-100)
            verbose: Whether to show verbose logging
            logger_name: Name for the logger
        """
        self.form_class = form_class
        self.api_key_env_var = api_key_env_var
        self.model_name = model_name
        self.role_prompt = role_prompt
        self.completion_threshold = completion_threshold
        self.verbose = verbose
        self.processor = None
        self.processor_session_id = None

        # Set up logging
        self.logger = SimpleLogger(logger_name)
        self.logger.set_agents_logs_visible(verbose)
        self.logger = self.logger.bind(
            session_id=f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        # Create console for formatted output
        self.console = LogConsole(name=logger_name)

    async def get_user_input(self, prompt: str = "\n💬 Your answer (type 'exit' to quit): ") -> str:
        """Get input from user asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(None, _sync_get_input, prompt)

    def setup(self) -> bool:
        """Initialize the processor with user preferences."""
        # Get API key from environment
        api_key = os.environ.get(self.api_key_env_var)
        if not api_key:
            self.logger.error(f"{self.api_key_env_var} environment variable not set")
            print(f"\n❌ {self.api_key_env_var} environment variable is not set. Please set it and try again.")
            return False

        # Initialize processor
        try:
            self.logger.info("Initializing FormProcessor...")
            self.processor = FormProcessor(
                form_class=self.form_class,
                api_key=api_key,
                model_name=self.model_name,
                completion_threshold=self.completion_threshold,
                role_prompt=self.role_prompt,
                verbose=self.verbose
            )
            self.logger.info("Form processor initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize processor: {e}")
            print(f"\n❌ Processor initialization error: {e}")
            return False

    async def initialize_session(self, user_id: str = "interactive_user") -> Optional[FormData]:
        """Initialize session asynchronously."""
        if not self.processor:
            self.logger.error("Processor not initialized")
            return None

        self.processor_session_id = await self.processor.start_session(user_id)
        self.logger = self.logger.bind(processor_session_id=self.processor_session_id)
        self.logger.success("Session started successfully")

        # Get initial response
        form_data = await self.processor.get_form_state(self.processor_session_id)
        initial_message = form_data.session_info.metadata.next_message_ai or "Hello! I'll help you fill out the form. Let's begin!"

        # Получаем актуальные данные формы напрямую из базы данных
        raw_form_data = await self.processor.session_manager.get_latest_form_data(str(self.processor_session_id))

        # Извлекаем user_form из полученных данных
        form_data_dict = raw_form_data["user_form"]
        self.logger.info(f"Displaying initial form data directly from DB: {json.dumps(form_data_dict, indent=2, ensure_ascii=False)}")
        self.console.print_json(message="Initial form data (from DB)", data=form_data_dict)

        # Then AI greeting
        print(f"\n🤖 {initial_message}")

        return form_data

    async def process_user_message(self, user_message: str) -> Optional[FormData]:
        """Process a single user message."""
        if not self.processor or not self.processor_session_id:
            self.logger.error("Processor or session not initialized")
            return None

        self.logger.info(f"Processing user message: {user_message}")
        response = await self.processor.process_message(user_message, str(self.processor_session_id))

        # Show progress
        progress = response.session_info.metadata.progress
        progress_bar = create_progress_bar(progress)
        print(f"\n📊 Form completion: {progress_bar}")

        # Получаем актуальные данные формы напрямую из базы данных
        raw_form_data = await self.processor.session_manager.get_latest_form_data(str(self.processor_session_id))

        # Извлекаем user_form из полученных данных
        if raw_form_data and isinstance(raw_form_data, dict) and "user_form" in raw_form_data:
            form_data_dict = raw_form_data["user_form"]
            self.logger.info(f"Displaying form data directly from DB: {json.dumps(form_data_dict, indent=2, ensure_ascii=False)}")
            self.console.print_json(message="Current form data (from DB)", data=form_data_dict)
        else:
            self.logger.warning("No user_form data found in DB, displaying from response")
            # Fallback к данным из ответа
            self.console.print_json(message="Current form data", data=response.session_info.user_form.model_dump())

        # Show AI response AFTER form data output
        print(f"\n🤖 {response.session_info.metadata.next_message_ai}")

        return response

    async def handle_form_completion(self, response: FormData) -> bool:
        """Handle form completion if achieved."""
        if not response:
            return False

        if response.system.completion_achieved:
            self.logger.success("Form reached completion threshold!")

            if response.analytics:
                print("\n📈 Form analysis completed!")
                return True

        return False

    def print_analytics(self, form_data: FormData, detailed: bool = True) -> None:
        """
        Print analytics information using the LogConsole.

        Args:
            form_data: The FormData object containing form data and analytics
            detailed: Whether to print detailed analytics or just a summary
        """
        # Create an analytics summary dictionary
        analytics_data = {}

        # First add the form data with proper structure
        user_form = form_data.session_info.user_form

        # Add common fields from the form itself
        form_data_dict = user_form.model_dump()
        analytics_data["form_data"] = form_data_dict

        # Add analytics information if available
        if form_data.analytics:
            # Create a structured representation of analytics
            analytics = form_data.analytics
            analytics_summary = {
                "completion_score": f"{form_data.session_info.metadata.progress}%",
                "key_insights": analytics.key_insights if hasattr(analytics, "key_insights") else [],
                "recommendations": analytics.recommendations if hasattr(analytics, "recommendations") else [],
                "sentiment": analytics.sentiment_analysis if hasattr(analytics, "sentiment_analysis") else {},
                "data_quality": analytics.data_quality_score if hasattr(analytics, "data_quality_score") else None
            }

            # Add more detailed analytics if requested
            if detailed and hasattr(analytics, "data_analysis"):
                analytics_summary["detailed_analysis"] = analytics.data_analysis

            analytics_data["analytics"] = analytics_summary

        # Use the console to print the structured data
        self.console.print_json(message="Form Analytics", data=analytics_data)

    async def run_interactive_session(self) -> None:
        """Run a complete interactive session."""
        print(f"🚀 Starting interactive form filling session for {self.form_class.__name__}\n")
        print("This interactive session allows you to fill out a form through dialogue.")
        print("Type 'exit' at any time to exit the dialogue.\n")

        # Initialize session and processor
        if not self.setup():
            return

        try:
            # Initialize session asynchronously
            await self.initialize_session()

            # Main loop
            user_message = await self.get_user_input()

            while user_message.lower() not in ['exit', 'quit', 'q']:
                # Process message asynchronously
                response = await self.process_user_message(user_message)

                if not response:
                    print("\n❌ Failed to process message")
                    break

                # Check if form is complete
                form_completed = await self.handle_form_completion(response)

                if form_completed and response.analytics:
                    # Using a direct approach without questionary for analytics display
                    print("\n📈 Form analysis completed!")
                    show_analytics = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("Show analytics? (y/n): ").lower().startswith('y')
                    )
                    if show_analytics:
                        # Use our new method to print analytics in a structured way
                        self.print_analytics(response)

                    # And for continuation question
                    continue_conversation = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("Would you like to continue the conversation? (y/n): ").lower().startswith('y')
                    )
                    if not continue_conversation:
                        print("\n👋 Thanks for filling out the form!")
                        break

                # Get next user message
                user_message = await self.get_user_input()

            print("\n👋 Ending dialogue. Thank you for your time!")

        except Exception as e:
            self.logger.exception(f"Error during conversation: {e}")
            print(f"\n❌ An error occurred: {e}")

    @classmethod
    async def run_with_form(
        cls,
        form_class: Type[BaseFormModel],
        api_key_env_var: str = "OPENROUTER_API_KEY",
        model_name: str = "openai/gpt-4o-2024-11-20",
        role_prompt: str = "",
        completion_threshold: int = 100,
        verbose: bool = True,
        logger_name: str = "examples.interactive"
    ) -> None:
        """
        Class method to directly run an interactive session with a form class.

        Args:
            form_class: The form model class to use
            api_key_env_var: Environment variable name containing the API key
            model_name: The LLM model to use
            role_prompt: Custom instructions for the LLM
            completion_threshold: Threshold to consider the form complete (0-100)
            verbose: Whether to show verbose logging
            logger_name: Name for the logger
        """
        try:
            session = cls(
                form_class=form_class,
                api_key_env_var=api_key_env_var,
                model_name=model_name,
                role_prompt=role_prompt,
                completion_threshold=completion_threshold,
                verbose=verbose,
                logger_name=logger_name
            )
            await session.run_interactive_session()
            print("\n✅ Interactive session completed")
        except KeyboardInterrupt:
            print("\n\n👋 Program interrupted. Shutting down.")
        except Exception as e:
            logger = SimpleLogger(logger_name)
            logger.exception(f"Unhandled error in interactive session: {e}")
            print(f"\n❌ An unhandled error occurred: {e}")
