"""OpenRouter provider for LLM services."""

# import logging # Removed unused import
import logging
import json
from typing import Dict, Any, Optional, List, Union
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from ...utils import SimpleLogger

# Disable logging for OpenAI and HTTPX libraries
# This prevents automatic DEBUG logs from AsyncOpenAI client
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)
logging.getLogger("openai._response").setLevel(logging.WARNING)
logging.getLogger("openai._legacy_response").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


class LLMResponse:
    """Wraps the LLM response to provide simplified access to the content."""

    def __init__(self, response_data: Union[Dict[str, Any], ChatCompletion, str]):
        """Initializes the wrapper with the raw response data from the provider."""
        self.raw_response = response_data
        self._content = None
        self.logger = SimpleLogger("providers.openrouter")
        self._extract_content()

    def _extract_content(self):
        """Internal method to extract the main text content from different response structures."""
        try:
            # Direct string content
            if isinstance(self.raw_response, str):
                self._content = self.raw_response
            # Handle ChatCompletion object from openai
            elif isinstance(self.raw_response, ChatCompletion):
                if hasattr(self.raw_response, 'choices') and len(self.raw_response.choices) > 0:
                    if hasattr(self.raw_response.choices[0], 'message'):
                        self._content = self.raw_response.choices[0].message.content
            # Handle dict from OpenRouter
            elif isinstance(self.raw_response, dict) and 'choices' in self.raw_response:
                if isinstance(self.raw_response['choices'], list) and len(self.raw_response['choices']) > 0:
                    choice = self.raw_response['choices'][0]
                    if isinstance(choice, dict) and 'message' in choice:
                        self._content = choice['message'].get('content', '')
            # Fallback for unknown format
            else:
                if self.logger:
                    self.logger.warning(f"Unknown response format: {type(self.raw_response)}")  # Log warning
                self._content = str(self.raw_response)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error extracting content from response: {e}")  # Log error
            self._content = ""

    @property
    def content(self) -> str:
        """Returns the extracted response content as a string."""
        return self._content or ""

    def to_dict(self) -> Dict[str, Any]:
        """Converts the raw response data into a dictionary format."""
        if isinstance(self.raw_response, dict):
            return self.raw_response
        elif isinstance(self.raw_response, ChatCompletion):
            # Convert ChatCompletion to dict more safely
            try:
                return {
                    "id": getattr(self.raw_response, "id", "unknown"),
                    "object": getattr(self.raw_response, "object", "chat.completion"),
                    "created": getattr(self.raw_response, "created", 0),
                    "model": getattr(self.raw_response, "model", "unknown"),
                    "content": self.content
                }
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error converting ChatCompletion to dict: {e}")  # Log error
                return {"content": self.content}
        else:
            return {"content": self.content}


class OpenRouterProvider:
    """
    Provides access to LLM models via the OpenRouter API.

    This class uses the `openai` library to interact with the OpenRouter
    endpoint, which mimics the OpenAI API structure.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "openai/gpt-4o-mini-2024-07-18",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 60,
        max_retries: int = 2,
    ):
        """
        Initializes the OpenRouter provider.

        Args:
            api_key: Your OpenRouter API key.
            model_name: The default model identifier to use (e.g., 'openai/gpt-4o-mini-2024-07-18').
            base_url: The base URL for the OpenRouter API.
            timeout: The request timeout in seconds.
            max_retries: The maximum number of retries for failed API requests.
        """
        self.logger = SimpleLogger("providers.openrouter")

        if not api_key:
            self.logger.error("API key is required for OpenRouterProvider")  # Log error
            raise ValueError("API key is required")

        self.api_key = api_key
        self.model_name = model_name

        # Create OpenAI client
        try:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries
            )
            self.logger.debug(f"Created OpenAI client for OpenRouter with model {model_name}")  # Log debug
        except Exception as e:
            self.logger.error(f"Error creating OpenAI client: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Sends a request to the chat completions endpoint.

        Args:
            messages: A list of message dictionaries (e.g., {"role": "user", "content": ...}).
            temperature: The sampling temperature.
            max_tokens: Optional maximum number of tokens to generate.

        Returns:
            An LLMResponse object wrapping the API response.
        """
        try:
            # Convert messages to proper format
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    formatted_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # Call the API
            kwargs = {
                "model": self.model_name,
                "messages": formatted_messages,
                "temperature": temperature
            }

            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

            self.logger.debug(f"Sending chat completion request to {self.model_name} with temperature {temperature}")  # Log debug
            response = await self.client.chat.completions.create(**kwargs)
            self.logger.debug("Received chat completion response.")  # Log debug

            return LLMResponse(response)

        except Exception as e:
            self.logger.error(f"Error in chat completion: {e}")  # Log error
            return LLMResponse(f"Error: {str(e)}")

    async def json_completion(
        self,
        prompt: str,
        system_message: str = "You are a helpful assistant that responds with JSON.",
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generates a chat completion with instructions to return JSON, and parses the result.

        Attempts to use the model's native JSON mode if available, otherwise parses the text content.

        Args:
            prompt: The user's prompt.
            system_message: The system message instructing the model.
            temperature: The sampling temperature.
            max_tokens: Optional maximum number of tokens to generate.

        Returns:
            A dictionary parsed from the JSON response. Returns an error dict if JSON parsing fails.
        """
        try:
            # Set up messages
            messages = [
                {"role": "system", "content": "Always return JSON object based on schema provided."},
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]

            response_obj = None  # Initialize response_obj
            # Request JSON format if supported
            try:
                # First try with response_format
                self.logger.debug("Attempting chat completion with JSON response format.")  # Log debug
                kwargs = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"}
                }
                response = await self.client.chat.completions.create(**kwargs)
                response_obj = LLMResponse(response)
                self.logger.debug("Received response using JSON response format.")  # Log debug
            except Exception as e:
                # Fallback to regular completion
                self.logger.warning(f"JSON response_format not supported or failed: {e}, falling back to regular completion")  # Log warning
                response_obj = await self.chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            # Parse JSON response
            try:
                parsed_json = json.loads(response_obj.content)
                self.logger.debug("Successfully parsed JSON response.")  # Log debug
                return parsed_json
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {e}")  # Log error with snippet
                self.logger.error(response_obj.content)
                # If we can't parse JSON, wrap the content in a basic JSON structure
                return {"error": "Failed to parse JSON", "content": response_obj.content}

        except Exception as e:
            self.logger.error(f"Error in json_completion: {e}")  # Log error
            return {"error": str(e)}
