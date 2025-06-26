"""Form wizard implementation."""

import os
import traceback
from typing import Optional, Type, List, Dict, Any

from ...core.processor import FormProcessor
from ...models.form import BaseFormModel, FormData
from ....utils import SimpleLogger
from ...core.session import MessageHistory

from .models import SetupRequest
from .settings import Settings
from .form_generator import FormGenerator, CompleteFormStructure


class FormWizard:
    """
    FormWizard provides a simplified interface for working with the FormProcessor
    with predefined parameters specifically tailored for form creation wizards.
    """

    def __init__(
        self,
        api_key: str,
        form_class: Type[BaseFormModel] = SetupRequest,
        model_name: str = Settings.model_name,
        temperature: float = Settings.temperature,
        role_prompt: str = Settings.role_prompt,
        completion_threshold: int = 90,
        verbose: bool = False,
        logger_name: str = "wizzards.form"
    ):
        """
        Initialize the FormWizard with API key and optional custom parameters.

        Args:
            api_key: API key for OpenRouter or similar service
            form_class: The form model class (defaults to SetupRequest)
            model_name: LLM model to use
            temperature: Temperature for model generation (0.0-1.0)
            role_prompt: Custom instructions for the LLM (if None, uses DEFAULT_PROMPT)
            completion_threshold: Form completion percentage threshold
            verbose: Whether to enable verbose logging
            logger_name: Name for the logger
        """
        self.api_key = api_key
        self.form_class = form_class
        self.model_name = model_name
        self.temperature = temperature
        self.role_prompt = role_prompt or self.DEFAULT_PROMPT
        self.completion_threshold = completion_threshold
        self.verbose = verbose
        self.logger_name = logger_name

        # Set up logging
        self.logger = SimpleLogger(logger_name)
        self.logger.set_agents_logs_visible(verbose)

        # Initialize processor
        self.processor = FormProcessor(
            form_class=self.form_class,
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=self.temperature,
            completion_threshold=self.completion_threshold,
            role_prompt=self.role_prompt,
            verbose=self.verbose
        )

        self.session_id = None
        self.logger.info("FormWizard initialized successfully")

    async def start_session(self, user_id: str = "form_wizard_user") -> str:
        """
        Start a new session with the form processor.

        Args:
            user_id: User identifier

        Returns:
            Session ID for the new session
        """
        try:
            self.session_id = await self.processor.start_session(user_id)
            self.logger.info(f"Started new session: {self.session_id}")
            return self.session_id
        except Exception as e:
            self.logger.error(f"Error starting session: {e}")
            self.logger.error(traceback.format_exc())
            raise

    async def process_message(self, message: str, session_id: Optional[str] = None) -> FormData:
        """
        Process a user message and update the form state.

        Args:
            message: User's message content
            session_id: Session ID (if None, uses the current session)

        Returns:
            Updated FormData object
        """
        sid = session_id or self.session_id
        if not sid:
            self.logger.error("No active session ID")
            raise ValueError("No active session ID. Call start_session() first.")

        try:
            response = await self.processor.process_message(message, sid)
            self.logger.info(f"Processed message in session {sid}")
            return response
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.logger.error(traceback.format_exc())
            raise

    async def get_form_state(self, session_id: Optional[str] = None) -> FormData:
        """
        Get the current form state for a session.

        Args:
            session_id: Session ID (if None, uses the current session)

        Returns:
            Current FormData object
        """
        sid = session_id or self.session_id
        if not sid:
            self.logger.error("No active session ID")
            raise ValueError("No active session ID. Call start_session() first.")

        try:
            form_data = await self.processor.get_form_state(sid)
            self.logger.info(f"Retrieved form state for session {sid}")
            return form_data
        except Exception as e:
            self.logger.error(f"Error getting form state: {e}")
            self.logger.error(traceback.format_exc())
            raise

    async def get_message_history(
        self,
        session_id: Optional[str] = None,
    ) -> List[MessageHistory]:
        """
        Get message history for a session.

        Args:
            session_id: Session ID (if None, uses the current session)
            limit: Maximum number of messages to retrieve

        Returns:
            List of message history objects
        """
        sid = session_id or self.session_id
        if not sid:
            self.logger.error("No active session ID")
            raise ValueError("No active session ID. Call start_session() first.")

        try:
            messages = await self.processor.session_manager.get_messages(sid)
            self.logger.info(f"Retrieved {len(messages)} messages for session {sid}")
            return messages
        except Exception as e:
            self.logger.error(f"Error getting message history: {e}")
            self.logger.error(traceback.format_exc())
            raise

    async def generate_form_structure(self, user_form: Dict[str, Any]) -> CompleteFormStructure:
        """
        Generate a complete form structure based on the user's form data.

        This method uses a single request to generate the entire form structure including
        all fields and relationships, rather than the previous multi-step approach.

        Args:
            user_form: User's form data collected during the conversation

        Returns:
            Complete form structure with all forms and fields
        """
        try:
            self.logger.info("Generating form structure...")

            # Create a FormGenerator instance
            form_generator = FormGenerator(
                wizard_data=user_form,
                model_name=self.model_name,
                api_key=self.api_key
            )

            # Generate the complete form structure in a single request
            form_structure = await form_generator.generate_complete_structure()

            self.logger.info(f"Form structure generated successfully with {len(form_structure.forms)} forms")
            return form_structure

        except Exception as e:
            self.logger.error(f"Error generating form structure: {e}")
            self.logger.error(traceback.format_exc())
            raise

    @classmethod
    def from_env(
        cls,
        env_var: str = "OPENROUTER_API_KEY",
        **kwargs
    ) -> 'FormWizard':
        """
        Create a FormWizard instance using an API key from environment variables.

        Args:
            env_var: Name of environment variable containing the API key
            **kwargs: Additional arguments to pass to the FormWizard constructor

        Returns:
            FormWizard instance
        """
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"Environment variable {env_var} not set")

        return cls(api_key=api_key, **kwargs)

    def __getattr__(self, name):
        """
        Provide direct access to FormProcessor methods.

        This allows calling any FormProcessor method directly via the wizard.

        Args:
            name: Name of the attribute/method to access

        Returns:
            The requested attribute or method from the processor

        Raises:
            AttributeError: If the attribute doesn't exist on the processor
        """
        if hasattr(self.processor, name):
            return getattr(self.processor, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    @property
    def processor_instance(self):
        """
        Get direct access to the underlying FormProcessor instance.

        Returns:
            The FormProcessor instance
        """
        return self.processor
