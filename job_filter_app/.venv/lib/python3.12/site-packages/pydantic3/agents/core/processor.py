"""Form processor for handling user interaction."""

# import logging # Removed unused import
import traceback
from typing import Dict, Any, Optional, Type
import json

from pydantic import BaseModel

from ..models.form import FormData, BaseFormModel, FormMetadata, System, SessionInfo
from ..models.analytics import AnalyticsResult
from .agent import FormAgent
from .session import SessionManager
from ...utils import SimpleLogger
from ..utils.text_sanitizer import sanitize_text
from ..utils.model_factory import UniversalModelFactory


class FormProcessor:
    """
    Main entry point for form processing.

    This class ties together the form agent and session manager
    to provide a complete form processing solution.
    """

    def __init__(
        self,
        form_class: Type[BaseFormModel],
        api_key: str,
        role_prompt: str,
        model_name: str = "openai/gpt-4o-mini-2024-07-18",
        temperature: float = 0.1,
        db_path: Optional[str] = None,
        client_id: str = "default",
        completion_threshold: int = 100,
        verbose: bool = False
    ):
        """
        Initializes the FormProcessor.

        Args:
            form_class: The Pydantic model class defining the form structure.
            api_key: The API key for the LLM provider.
            role_prompt: An additional prompt defining the LLM's specific role during processing.
            model_name: The name of the LLM model to use.
            temperature: The sampling temperature for LLM generation.
            db_path: Optional path to the SQLite database file for session persistence.
            client_id: An identifier for the client application.
            completion_threshold: The progress percentage required to consider the form complete.
        """

        SimpleLogger.set_agents_logs_visible(verbose)

        # Create a logger for this class
        self.logger = SimpleLogger("core.processor")

        self.form_class = form_class
        self.client_id = client_id
        self.completion_threshold = completion_threshold
        self.role_prompt = role_prompt
        self.model_name = model_name  # Store model_name
        self.temperature = temperature  # Store temperature

        self.logger.info(f"FormProcessor initialized with completion_threshold: {self.completion_threshold}")

        # Validate inputs
        if not api_key:
            self.logger.error("API key is required")  # Log error directly
            raise ValueError("API key is required")

        if not issubclass(form_class, BaseModel):
            self.logger.error("Form class must be a subclass of BaseModel")  # Log error directly
            raise ValueError("Form class must be a subclass of BaseModel")

        try:
            self.agent = FormAgent(
                api_key=api_key,
                model_name=model_name,
                temperature=temperature,
            )
            self.logger.info(f"Form agent initialized with model {model_name}")  # Log info directly
        except Exception as e:
            self.logger.error(f"Failed to initialize form agent: {e}")
            raise ValueError(f"Failed to initialize form agent: {str(e)}")

        try:
            self.session_manager = SessionManager(
                db_path=db_path,
            )
            self.logger.info("Session manager initialized")  # Log info directly
        except Exception as e:
            self.logger.error(f"Failed to initialize session manager: {e}")
            raise ValueError(f"Failed to initialize session manager: {str(e)}")

    async def start_session(self, user_id: str) -> str:
        """
        Starts a new form processing session for a given user.

        Args:
            user_id: The unique identifier for the user.

        Returns:
            The newly created session identifier.
        """
        try:
            # Create a new session
            session_id = await self.session_manager.create_session(
                user_id=user_id,
                client_id=self.client_id,
                form_class=self.form_class.__name__
            )

            # Create empty form data with system config
            # Populate System model with session context
            system_config = System(
                completion_threshold=self.completion_threshold,
                completion_achieved=False,  # Initial state
                session_id=session_id,
                client_id=self.client_id,
                role_prompt=self.role_prompt,
                model_name=self.model_name,
                temperature=self.temperature,
                form_defaults=self.form_class().model_dump()
            )

            # Create SessionInfo with empty form
            session_info = SessionInfo(
                user_form=self.form_class()
            )

            # Create FormData with session_info and system config
            form_data = FormData(
                session_info=session_info,
                system=system_config  # Use the populated system config
            )

            # Save initial form data
            await self.session_manager.save_form_data(form_data, session_id)

            # Get the initial message language
            initial_language = form_data.session_info.metadata.next_message_language

            # Save welcome message with language
            await self.session_manager.save_message(
                role="assistant",
                content=form_data.session_info.metadata.next_message_ai,
                session_id=session_id,
                language=initial_language
            )

            self.logger.info(f"Started new session: {session_id}")  # Log info directly
            return session_id

        except Exception as e:
            self.logger.error(f"Error starting session: {e}")
            self.logger.error(traceback.format_exc())
            raise ValueError(f"Failed to start session: {str(e)}")

    async def process_message(
        self,
        message: str,
        session_id: str
    ) -> FormData:
        """
        Processes a user message within a specific session, updating the form state.

        Args:
            message: The user's message content.
            session_id: The identifier of the session to process the message in.

        Returns:
            The updated FormData object reflecting the changes after processing the message.
        """
        # Get session info to verify session exists
        session_info = await self.session_manager.get_session_info(session_id)
        if not session_info:
            self.logger.error(f"Session not found: {session_id}")  # Log error
            raise ValueError(f"Session not found: {session_id}")

        # Sanitize user input
        sanitized_message = sanitize_text(message)
        if message != sanitized_message:
            self.logger.info(f"Original message sanitized. Original: '{message}', Sanitized: '{sanitized_message}'")  # Log info

        # Set current session
        self.session_manager.session_id = session_id

        # Get message history
        message_history = await self.session_manager.get_messages(session_id)

        # Get latest form data to determine user language
        form_data_dict: Dict[str, Any] | None = await self.session_manager.get_latest_form_data(session_id)
        user_language = "en"  # Default language

        # Extract user language from metadata if available
        if form_data_dict and isinstance(form_data_dict, dict) and "metadata" in form_data_dict:
            metadata = form_data_dict.get("metadata", {})
            user_language = metadata.get("user_language", "en")

        # Save sanitized user message with the determined language
        await self.session_manager.save_message(
            role="user",
            content=sanitized_message,  # Save sanitized message
            session_id=session_id,
            language=user_language  # Use the user's language
        )

        # Get latest form data
        form_data_dict = await self.session_manager.get_latest_form_data(session_id)
        self.logger.info(f"Loaded form data dict from DB: {json.dumps(form_data_dict, indent=2, ensure_ascii=False) if form_data_dict else None}")  # Log info directly

        # Print detailed info about user_form data
        if form_data_dict and isinstance(form_data_dict, dict) and "user_form" in form_data_dict:
            self.logger.info(f"USER_FORM from DB: {json.dumps(form_data_dict['user_form'], indent=2, ensure_ascii=False)}")
        else:
            self.logger.warning("No user_form data found in DB")

        # Reconstruct form data from dict, including system config
        try:
            # Используем фабрику для создания формы без валидации
            factory = UniversalModelFactory(self.form_class, fill_data=False)
            form_instance = factory.build()

            # Заполняем данными из DB
            if form_data_dict and "user_form" in form_data_dict:
                for field_name, field_value in form_data_dict["user_form"].items():
                    if hasattr(form_instance, field_name):
                        setattr(form_instance, field_name, field_value)

            self.logger.info(f"Created form instance using factory: {json.dumps(form_instance.model_dump() if hasattr(form_instance, 'model_dump') else {}, indent=2)}")
        except Exception as e:
            self.logger.error(f"Error constructing form instance: {e}")
            # Last resort fallback
            factory = UniversalModelFactory(self.form_class, fill_data=False)
            form_instance = factory.build()

        metadata_dict = form_data_dict.get("metadata", {}) if form_data_dict else {}
        system_dict = form_data_dict.get("system", {}) if form_data_dict else {}
        analytics_dict = form_data_dict.get("analytics") if form_data_dict else None

        analytics_obj = None
        if analytics_dict:
            try:
                analytics_obj = AnalyticsResult.model_validate(analytics_dict)
            except Exception as analytics_exc:
                self.logger.error(f"Error reconstructing analytics in process_message: {analytics_exc}")

        # Create session_info first
        session_info = SessionInfo(
            user_form=form_instance,
            metadata=FormMetadata.model_validate(metadata_dict)
        )

        # Create FormData with session_info
        form_data = FormData(
            session_info=session_info,
            system=System.model_validate(system_dict),
            analytics=analytics_obj,
            history=message_history
        )
        # Process sanitized message with agent
        updated_form_data = await self.agent.process_message(
            message=sanitized_message,  # Use sanitized message
            form_data=form_data,
            form_class=self.form_class,
            message_history=message_history,
            role_prompt=self.role_prompt
        )

        # Determine assistant message language from next_message_language
        assistant_language = updated_form_data.session_info.metadata.next_message_language

        # Save assistant message with the proper language
        await self.session_manager.save_message(
            role="assistant",
            content=updated_form_data.session_info.metadata.next_message_ai,
            session_id=session_id,
            language=assistant_language  # Use the assistant's response language
        )

        # Save updated form data
        await self.session_manager.save_form_data(
            form_data=updated_form_data,
            session_id=session_id
        )

        # Return message history
        latest_messages = await self.session_manager.get_messages(session_id)
        updated_form_data.history = latest_messages

        self.logger.info(f"Message processed: progress={updated_form_data.session_info.metadata.progress}%")  # Log info directly

        return updated_form_data

    async def get_form_state(
        self,
        session_id: str
    ) -> FormData:
        """
        Retrieves the latest form state for a given session as a FormData object.

        Args:
            session_id: The identifier of the session.

        Returns:
            The FormData object representing the latest state.
            Returns an empty FormData object if the session or state is not found or fails to reconstruct.
        """
        if not session_id:
            self.logger.error("Session ID is required in get_form_state")  # Log error
            raise ValueError("Session ID is required")

        try:
            # Set current session
            self.session_manager.session_id = session_id

            # Get latest form data
            form_data_dict: Dict[str, Any] | None = await self.session_manager.get_latest_form_data(session_id)

            self.logger.info(f"Loaded form data dict from DB: {json.dumps(form_data_dict, indent=2, ensure_ascii=False) if form_data_dict else None}")  # Log info directly

            # Print detailed info about user_form data
            if form_data_dict and isinstance(form_data_dict, dict) and "user_form" in form_data_dict:
                self.logger.info(f"USER_FORM from DB in get_form_state: {json.dumps(form_data_dict['user_form'], indent=2, ensure_ascii=False)}")
            else:
                self.logger.warning("No user_form data found in DB in get_form_state")

            if not form_data_dict:
                self.logger.warning(f"No form data found for session {session_id} in get_form_state, returning empty.")  # Log warning directly
                # Return empty form data if none exists, including system config
                # Create session_info with empty form
                session_info = SessionInfo(
                    user_form=UniversalModelFactory(self.form_class, fill_data=False).build(),
                    metadata=FormMetadata(),
                )

                # Return FormData with session_info
                return FormData(
                    session_info=session_info,
                    system=System(completion_threshold=self.completion_threshold),
                    history=[],
                )

            # Reconstruct form data from dict
            try:
                # Используем фабрику для создания формы
                factory = UniversalModelFactory(self.form_class, fill_data=False)
                form_instance = factory.build()

                # Заполняем данными из DB
                if form_data_dict and "user_form" in form_data_dict:
                    user_form_dict = form_data_dict.get("user_form", {})
                    self.logger.debug(f"Filling form with data: {json.dumps(user_form_dict, indent=2, ensure_ascii=False)}")

                    # Явно заполняем поля данными для гарантии
                    for field_name, field_value in user_form_dict.items():
                        if hasattr(form_instance, field_name):
                            setattr(form_instance, field_name, field_value)
                            self.logger.debug(f"Set field {field_name} = {field_value}")

                self.logger.info(f"Created form instance for get_form_state: {json.dumps(form_instance.model_dump() if hasattr(form_instance, 'model_dump') else {}, indent=2, ensure_ascii=False)}")

                metadata_dict = form_data_dict.get("metadata", {}) if form_data_dict else {}
                system_dict = form_data_dict.get("system", {}) if form_data_dict else {}
                history = await self.session_manager.get_messages(session_id)
                analytics_dict = form_data_dict.get("analytics") if form_data_dict else None

                # Reconstruct analytics if present
                analytics_obj = None
                if analytics_dict:
                    try:
                        analytics_obj = AnalyticsResult.model_validate(analytics_dict)
                    except Exception as analytics_exc:
                        self.logger.error(f"Error reconstructing analytics in get_form_state: {analytics_exc}")
                        # Keep analytics_obj as None if reconstruction fails

                # Create session_info
                session_info = SessionInfo(
                    user_form=form_instance,
                    metadata=FormMetadata.model_validate(metadata_dict),
                )

                # Create form_data with session_info
                form_data = FormData(
                    session_info=session_info,
                    system=System.model_validate(system_dict),
                    analytics=analytics_obj,
                    history=history
                )

                return form_data
            except Exception as e:
                self.logger.error(f"Error reconstructing form data in get_form_state: {e}")
                self.logger.error(traceback.format_exc())
                # Fallback to empty form data on reconstruction error, including system config
                # Create session_info with empty form
                session_info = SessionInfo(
                    user_form=UniversalModelFactory(self.form_class, fill_data=False).build(),
                    metadata=FormMetadata(),
                )

                # Return FormData with session_info
                return FormData(
                    session_info=session_info,
                    system=System(completion_threshold=self.completion_threshold),
                    history=[],
                )

        except Exception as e:
            self.logger.error(f"Error getting form state: {e}")
            self.logger.error(traceback.format_exc())
            # Fallback to empty form data on general error, including system config
            # Create session_info with empty form
            session_info = SessionInfo(
                user_form=UniversalModelFactory(self.form_class, fill_data=False).build(),
                metadata=FormMetadata(),
            )

            # Return FormData with session_info
            return FormData(
                session_info=session_info,
                system=System(completion_threshold=self.completion_threshold),
                history=[],
            )

    async def get_latest_progress(
        self,
        session_id: str
    ) -> int:
        """
        Retrieves the latest progress percentage for a given session.

        Args:
            session_id: The identifier of the session.

        Returns:
            The progress percentage (0-100) of the latest form state.
            Returns 0 if no form data is found or an error occurs.
        """
        if not session_id:
            self.logger.error("Session ID is required in get_latest_progress")
            raise ValueError("Session ID is required")

        try:
            # Get latest form data from the session manager
            form_data_dict = await self.session_manager.get_latest_form_data(session_id)

            # Extract progress from metadata if available
            if form_data_dict and isinstance(form_data_dict, dict) and "metadata" in form_data_dict:
                metadata = form_data_dict.get("metadata", {})
                progress = metadata.get("progress", 0)

                # Ensure progress is an integer
                if isinstance(progress, float):
                    progress = int(progress)
                elif not isinstance(progress, int):
                    self.logger.warning(f"Progress value is not int or float: {progress}. Defaulting to 0.")
                    progress = 0

                self.logger.info(f"Retrieved latest progress for session {session_id}: {progress}%")
                return progress
            else:
                self.logger.warning(f"No metadata found for session {session_id}, returning progress 0")
                return 0

        except Exception as e:
            self.logger.error(f"Error getting latest progress: {e}")
            self.logger.error(traceback.format_exc())
            return 0
