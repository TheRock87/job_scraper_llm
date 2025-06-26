"""Form agent for handling form processing."""

import json
from typing import Type, List
import traceback
from datetime import datetime
from .session import SessionManager
from ..models.form import FormData, BaseFormModel, MessageHistory
from ..models.analytics import AnalyticsResult
from ..providers.openrouter import OpenRouterProvider
from ..utils.helper import Helper
from ..utils.model_factory import UniversalModelFactory
from ..models.form import UserInfo
from ...utils import SimpleLogger


class Config:
    BOT_NAME = "Reforma"
    BOT_GENDER = "female"
    SITE_URL = "https://reforms.ai"


class FormAgent:
    """
    Agent responsible for processing user messages, extracting form data,
    and generating analytics based on the completed form.
    It interacts directly with an LLM provider.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "openai/gpt-4o-mini-2024-07-18",
        temperature: float = 0.1,
        max_tokens: int = 100000,
    ):
        """
        Initializes the FormAgent.

        Args:
            api_key: API key for the LLM provider.
            model_name: Name of the LLM model to use.
            temperature: Default sampling temperature for LLM generations.
        """

        self.logger = SimpleLogger("core.agent")
        self.temperature = temperature
        self.max_tokens = max_tokens
        # Initialize provider
        try:
            self.provider = OpenRouterProvider(
                api_key=api_key,
                model_name=model_name,
            )
            self.logger.info(f"Initialized FormAgent with model {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM provider: {e}")
            raise ValueError(f"Failed to initialize LLM provider: {str(e)}")

    async def process_message(
        self,
        message: str,
        form_data: FormData,
        form_class: Type[BaseFormModel],
        message_history: List[MessageHistory] = [],
        role_prompt: str = ""
    ) -> FormData:
        """
        Processes a user message, updates the form data, and potentially generates analytics.

        Args:
            message: The user's message content.
            form_data: The current state of the form data (including metadata and system config).
            form_class: The Pydantic model class representing the form structure.
            message_history: A list of previous messages in the conversation.
            role_prompt: An additional prompt defining the specific role for the LLM.

        Returns:
            The updated FormData object.
        """

        # First process the message to update form data
        updated_form_data = await self._extract_form_info(message, form_data, form_class, message_history, role_prompt)

        # Then check if we need to generate analytics
        if updated_form_data.system.completion_achieved and updated_form_data.analytics is None:
            self.logger.info("Completion threshold reached. Generating analytics.")
            updated_form_data = await self._generate_analytics(message, updated_form_data, form_class, message_history)

        return updated_form_data

    def _trim(self, text: str) -> str:
        """Trim lines and remove extra spaces."""
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())

    async def _extract_form_info(
        self,
        message: str,
        form_data: FormData,
        form_class: Type[BaseFormModel],
        message_history: List[MessageHistory],
        role_prompt: str = ""
    ) -> FormData:
        """
        Extract information from user message and update form.

        Args:
            message: User message
            form_data: Current form data
            form_class: Form class
            message_history: Message history
            role_prompt: Additional prompt text for role customization

        Returns:
            Updated form data
        """
        try:
            self.logger.debug("Agent: Entering _extract_form_info")

            # Get form schema for form illustration
            form_schema = form_class.model_json_schema()

            # Get session_info dump for LLM to process
            self.logger.debug("Agent: Attempting to dump session_info...")

            # Properly serialize form data and metadata
            try:
                user_form_data = form_data.session_info.user_form.model_dump(mode="json")
                metadata_data = form_data.session_info.metadata.model_dump(mode="json")
            except Exception as e:
                self.logger.error(f"Agent: Error serializing user_form or metadata: {e}")
                user_form_data = {}
                metadata_data = {}

            self.logger.debug("Agent: Session info dumped successfully.")

            # Prepare prompt for information extraction
            self.logger.debug("Agent: Preparing system message...")

            # Prepare history for the LLM
            history_data = []
            last_messages = message_history[-5:]
            for msg in last_messages:
                history_data.append(
                    f"{msg.role}: {msg.content}"
                )

            system_message = f"""
            You are an AI assistant named {Config.BOT_NAME}.
            Your default website is {Config.SITE_URL}.
            You are a {Config.BOT_GENDER}.

            Your job is to:
            1. Extract relevant information from user messages to fill form fields.
            2. Update the form data with extracted information.
            3. Calculate the form completion progress (0–100%).
            4. Generate the next helpful, engaging question to continue the form.
            5. Detect the user's language and reply in it.
            6. Engage in light, friendly conversation if the user initiates small talk — but always return to form filling.

            [REQUIREMENTS]
            - Be very friendly and conversational — like a human assistant.
            - If the user provides relevant information, thank them and ask the next related question.
            - If the user doesn't provide useful information, kindly remind them what is needed.
            - If the user asks YOU a question (e.g., "How are you?", "What's your name?", "Are you real?") — answer briefly and bring the conversation back to the form.
            - If the user asks something completely unrelated, let them know you're here to help with the form and guide them back.
            - Use the same language the user is using (auto-detect if needed).
            {role_prompt}
            [/REQUIREMENTS]
            """
            system_message = self._trim(system_message)

            self.logger.debug("Agent: System message prepared.", system_message)
            self.logger.debug("Agent: Preparing prompt string...")

            prompt_blocks_str = "\n".join([
                self._make_block("DATE_NOW", datetime.now().strftime("%Y-%m-%d")),
                self._make_block("CURRENT_PROGRESS", f"{form_data.session_info.metadata.progress}%"),
                self._make_block("PREV_QUESTION", form_data.session_info.metadata.previous_question),
                self._make_block("USER_ANSWER", message),
                self._make_block("FORM_SCHEMA", json.dumps(form_schema, indent=2, ensure_ascii=False)),
                self._make_block("USER_FORM", Helper.data_to_yaml(user_form_data)),
                self._make_block("METADATA", Helper.data_to_yaml(metadata_data)),
                self._make_block("MESSAGE_HISTORY", Helper.data_to_yaml(history_data)),
            ])

            prompt_extra = """

            🎯 TASK:
            Your goal is to extract useful information from the [USER_ANSWER] and [MESSAGE_HISTORY], improve the form, and move the conversation forward.

            ### 1. USER_FORM
            - Improve the current form fields based on new inputs.
            - Only update what is clearly stated — never guess.
            - Keep enums/allowed values exactly as defined in [FORM_SCHEMA].
            - If a user response appears unrealistic or clearly incorrect (e.g. a phone number with letters, a date in the future, an email without '@'), do not add it to the form.
            - In such cases, politely ask the user to clarify or provide a valid input.
            - Be cautious with data like age, phone, email, dates — verify that they make sense before updating the form.
            - Don't create own ideas for the form, use only what user provided.

            👉 If the user's answer seems incomplete, vague, or inconsistent:
            - Don't blindly accept it — politely ask for clarification or confirmation.
            - Example prompts:
            - "Just to double-check — did you mean [X]?"
            - "That doesn't seem like a valid [field] — could you rephrase it?"
            - "Can you please clarify what you meant by '[user input]'?"

            Always prioritize clarity and data accuracy over speed of completion.

            ### 💡 INPUT FORMAT GUIDELINES
            - Never ask the user to enter information in a specific format (e.g., "Please enter your date of birth as YYYY-MM-DD").
            - Instead, ask the question in a natural, conversational way (e.g., "When is your birthday?").
            - Accept whatever format the user provides and normalize the input internally.
            - Use emoji (but not often) to make the conversation more lively.

            ### 2. METADATA
            - Update `progress` (never decrease it).
            - Detect `user_language` from message content.
            - Enrich `user_info` if any personal data (like name, email, age) is present.
            - Add or update `next_message_ai` — your response to the user.

            ### 3. NEXT_MESSAGE_AI Rules:

            If the user asked about you (e.g., "What's your name?", "How are you?"):
            - Respond briefly and kindly.
            - Then smoothly return to the form with a helpful follow-up question.

            If the user asked an unrelated question:
            - Be polite but explain you're here to help with a form, and guide them back.

            If the user provided relevant info:
            - Acknowledge what you understood first (briefly summarize or rephrase the user's input).
            - Then thank them and ask the next related question.
            - Example: "Thanks! Red is a beautiful color. Now, could you tell me..."

            If the message is unclear or not related to previous ones:
            - Politely ask the user to clarify or restate their answer.

            ### 4. FLEXIBLE FORM FILLING
            - If the user's response provides enough context to fill other form fields, try to complete them immediately, without waiting for answers to all other questions.
            - Save the user's effort by filling out the form more quickly and logically based on their responses to avoid unnecessary steps.
            - If the form allows skipping steps that aren't relevant to the previous answer, do so to speed up the process.
            - **Do not ignore required fields** in the form schema — ensure that all mandatory fields are filled, even if other fields are completed out of order.

            ### Other:
            - Try to ask the next logical group of questions that will help fill the form faster.
            - Always keep the tone warm, friendly, and conversational.
            - Always respond in the same language as the user.
            - If the user gives an especially interesting, creative, or thoughtful answer — don't hesitate to **genuinely compliment** them or show appreciation (e.g., "That's a great answer!", "Wow, that's an interesting way to put it!", "Love that response.").

            Return a valid JSON object with the updated (based in [FORM_SCHEMA]):
            - "user_form"
            - "metadata"
            - "next_message_ai"
            - "next_message_language"
            - "user_language"
            - "user_info"
            """

            # Join blocks and extra prompt
            prompt = prompt_blocks_str + "\n\n---\n\n" + self._trim(prompt_extra)

            self.logger.debug("Agent: Prompt string prepared.", prompt)

            # Get response from LLM
            self.logger.info("Agent: Calling LLM provider for form info extraction...")
            response = await self.provider.json_completion(
                prompt=prompt,
                system_message=system_message,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            self.logger.info("Agent: Received response from LLM provider")

            # Extract response as JSON
            response_json = response if isinstance(response, dict) else {}
            self.logger.debug(f"Agent: Received LLM response JSON: {json.dumps(response_json, indent=2, ensure_ascii=False)}")

            if not response_json:
                self.logger.error("Empty response from LLM during form info extraction")
                return self._create_error_response(form_data, "I encountered an error processing your information.")

            # Extract session_info from response
            session_info_data = response_json.get("session_info", {})
            if not session_info_data:
                self.logger.warning("No session_info in LLM response, trying legacy format")
                # Try legacy format where user_form and metadata are at the top level
                user_form_data = response_json.get("user_form", {})
                metadata_data = response_json.get("metadata", {})
                if user_form_data or metadata_data:
                    session_info_data = {
                        "user_form": user_form_data,
                        "metadata": metadata_data
                    }

            if not session_info_data:
                self.logger.error("No valid session_info structure in LLM response")
                return self._create_error_response(form_data, "I encountered an error processing your information.")

            # Extract components from session_info
            user_form_data = session_info_data.get("user_form", {})
            metadata_data = session_info_data.get("metadata", {})

            # Get progress and ensure it's an integer
            # Log the progress value obtained from the response (or default) at DEBUG level
            progress_from_llm = metadata_data.get("progress")  # Try getting from metadata
            self.logger.debug(f"Agent: Progress value directly from LLM response: {progress_from_llm}")  # <<< Log raw progress
            progress = progress_from_llm if progress_from_llm is not None else form_data.session_info.metadata.progress
            self.logger.debug(f"Agent: Progress value to use (after default): {progress}")  # <<< Log final progress value

            if isinstance(progress, float):
                self.logger.debug(f"Agent: Converting float progress {progress} to int.")
                progress = int(progress)
            elif not isinstance(progress, int):
                self.logger.warning(f"Agent: Progress value is not int or float ({type(progress)}): {progress}. Defaulting to current progress: {form_data.session_info.metadata.progress}")
                progress = form_data.session_info.metadata.progress  # Fallback safely

            # Update metadata and completion status using the new method
            form_data.update_progress(progress)  # Updates self.metadata.progress & self.system.completion_achieved

            # Update user_form with new data if provided
            if user_form_data:
                self.logger.info(f"Agent: Updating form with new data from LLM: {json.dumps(user_form_data, indent=2, ensure_ascii=False)}")
                try:
                    # Просто создаем новый экземпляр формы с данными от LLM
                    # LLM уже должен вернуть полную форму со всеми данными
                    factory = UniversalModelFactory(form_class, fill_data=False)
                    new_form = factory.build()

                    # Заполняем данными от LLM
                    for field_name, field_value in user_form_data.items():
                        if hasattr(new_form, field_name):
                            setattr(new_form, field_name, field_value)

                    # Обновляем форму
                    form_data.session_info.user_form = new_form
                    self.logger.info("Agent: Form updated successfully")
                except Exception as e:
                    self.logger.error(f"Agent: Error updating form: {e}")
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.warning("Agent: LLM returned empty user_form data")

            # Update next_message_ai
            if "next_message_ai" in metadata_data:
                # Store current next_message_ai as previous_question before updating
                form_data.session_info.metadata.previous_question = form_data.session_info.metadata.next_message_ai
                form_data.session_info.metadata.next_message_ai = metadata_data.get("next_message_ai")

            # Update user_info if provided
            if metadata_data.get("user_info"):
                self.logger.info("Agent: Updating user_info with new data from LLM")
                try:

                    form_data.session_info.metadata.user_info = UserInfo.model_validate(metadata_data.get("user_info"))
                    self.logger.info(f"Agent: Updated user_info: {form_data.session_info.metadata.user_info.model_dump()}")
                except Exception as e:
                    self.logger.error(f"Agent: Error updating user_info: {e}")

            # Update user_language
            if "user_language" in metadata_data:
                form_data.session_info.metadata.user_language = metadata_data.get("user_language")

            self.logger.info(f"Form info extracted. Progress: {form_data.session_info.metadata.progress}%")
            return form_data

        except Exception as e:
            self.logger.error(f"Error extracting form info: {e}")
            self.logger.error(traceback.format_exc())
            return self._create_error_response(form_data, "I encountered an error processing your information.")

    @staticmethod
    def _make_block(tag: str, data: str) -> str:
        tag = tag.upper()
        return f"[{tag}] {data} [/{tag}]"

    async def _generate_analytics(
        self,
        message: str,
        form_data: FormData,
        form_class: Type[BaseFormModel],
        message_history: List[MessageHistory]
    ) -> FormData:
        """
        Generate analytics based on the completed form.

        Args:
            message: User message
            form_data: Current form data
            form_class: Form class
            message_history: Message history

        Returns:
            Updated form data with analytics
        """
        try:
            # Save a copy of the current form data
            current_user_form = form_data.session_info.user_form

            # Get the latest form data from the database
            session_id = form_data.system.session_id
            if session_id:
                self.logger.info(f"Agent: Getting latest form data from DB for session {session_id}")

                # Create SessionManager instance to access the database
                session_manager = SessionManager()

                # Get the latest form state from the database
                latest_form_data_dict = await session_manager.get_latest_form_data(session_id)

                if latest_form_data_dict:
                    self.logger.info("Agent: Successfully retrieved latest form data from DB")

                    # Extract only the form data from the retrieved dictionary
                    latest_user_form_data = latest_form_data_dict.get("user_form", {})

                    if latest_user_form_data:
                        self.logger.info(f"Agent: Found user_form data in DB: {json.dumps(latest_user_form_data, indent=2, ensure_ascii=False)}")

                        # Update the form with the retrieved data
                        try:
                            # Create new form instance and fill with DB data
                            factory = UniversalModelFactory(form_class, fill_data=False)
                            new_form = factory.build()

                            # Fill with data from DB
                            for field_name, field_value in latest_user_form_data.items():
                                if hasattr(new_form, field_name):
                                    setattr(new_form, field_name, field_value)

                            # Update form
                            current_user_form = new_form
                            self.logger.info("Agent: Updated form with data from DB")
                        except Exception as e:
                            self.logger.error(f"Agent: Error updating form with DB data: {e}")
                            self.logger.error(traceback.format_exc())
                    else:
                        self.logger.warning("Agent: DB record found but no user_form data in it")
                else:
                    self.logger.warning(f"Agent: No form data found in DB for session {session_id}")
            else:
                self.logger.warning("Agent: No session_id available, cannot retrieve form from DB")

            # Before getting data, output information about what we have at the start
            self.logger.debug(f"Agent: Starting analytics generation... Current form fields: {current_user_form.model_fields_set if hasattr(current_user_form, 'model_fields_set') else 'unknown'}")

            # Save a copy of the entire FormData structure before working with it
            # Try different ways to save data to ensure its safety
            current_user_form_dump = current_user_form.model_dump() if hasattr(current_user_form, "model_dump") else {}

            # Save the original form data for debugging
            self.logger.debug(f"Agent: Original form data: {json.dumps(current_user_form_dump, indent=2, ensure_ascii=False)}")

            # Prepare system message for analytics
            system_message = self._trim("""
            You are a data analysis assistant.
            Your task is to provide comprehensive insights based on submitted form data and user interaction history.
            Return ONLY a valid JSON object conforming exactly to the following JSON Schema.
            Do NOT include any other text or explanations outside the JSON object itself:
            """)

            analytics_schema = AnalyticsResult.model_json_schema()
            analytics_schema = json.dumps(analytics_schema, indent=2, ensure_ascii=False)

            # Prompt blocks
            prompt_blocks_str = "\n".join([
                self._make_block("SCHEMA", analytics_schema),
                self._make_block("FORM_DATA_TO_ANALYZE", Helper.data_to_yaml(current_user_form_dump)),
                self._make_block("LAST_USER_ANSWER", message),
                self._make_block("CONVERSATION_HISTORY", Helper.data_to_yaml(message_history[-5:])),
            ])

            # Prepare prompt for analytics generation
            prompt_extra = """
            Based on the Form Data, Last User Message, and Conversation History, perform the analysis tasks described in the system message.
            Return the complete analysis as a JSON object matching the [SCHEMA] provided.
            """

            # Join blocks and extra prompt
            prompt = prompt_blocks_str + "\n\n---\n\n" + self._trim(prompt_extra)

            # Get response from LLM
            response = await self.provider.json_completion(
                prompt=prompt,
                system_message=system_message,
                temperature=self.temperature * 1.2,  # Slightly higher temperature for creative analysis
                max_tokens=self.max_tokens
            )

            # Log response
            self.logger.info(f"Agent: LLM response for analytics: {json.dumps(response, indent=2, ensure_ascii=False)}")

            # Extract response as JSON
            response_json = response if isinstance(response, dict) else {}

            if not response_json:
                self.logger.error("Empty response from LLM during analytics generation")
                return self._create_error_response(form_data, "I encountered an error analyzing your information.")

            # Validate analytics data
            try:
                analytics_data = AnalyticsResult.model_validate(response_json)
                self.logger.info(f"Agent: Validated analytics data: {json.dumps(analytics_data.model_dump(), indent=2, ensure_ascii=False)}")
            except Exception as validation_error:
                self.logger.error(f"Analytics response validation failed: {validation_error}")
                # Use empty analytics as fallback
                analytics_data = AnalyticsResult.create_empty()

            # Update form with current data to ensure we're using the latest
            form_data.session_info.user_form = current_user_form

            # Update metadata
            form_data.session_info.metadata.next_message_ai = "Here is my analysis of your information."

            # Save analytics to FormData directly (not in metadata)
            form_data.analytics = analytics_data

            self.logger.info(f"Generated analytics for form: {form_data.session_info.user_form.__class__.__name__}")
            return form_data

        except Exception as e:
            self.logger.error(f"Error generating analytics: {e}")
            self.logger.error(traceback.format_exc())
            return self._create_error_response(form_data, "I encountered an error analyzing your information.")

    def _create_error_response(self, form_data: FormData, error_message: str) -> FormData:
        """Creates a generic error response to send back to the processor."""
        self.logger.warning(f"Creating error response: {error_message}")  # Log warning
        form_data.session_info.metadata.next_message_ai = "Something went wrong. Please try again later."
        # Potentially reset progress or add specific error metadata here if needed
        return form_data
