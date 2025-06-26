# pydantic3 Agents - Form Processing with LLM

Framework for extracting structured data from dialogues using LLM models via OpenRouter, with full support for Pydantic v2.

## Capabilities

- Extraction of data from user messages and form field population
- Calculation of completion progress and detection of completion moment
- Analytics generation for completed forms
- Conversation history tracking
- Form state and message persistence in database
- Error handling and recovery after failures
- Support for nested Pydantic models with proper serialization
- Compatibility with modern async frameworks

## Architecture

### Core

- `FormProcessor` - main entry point for applications
- `FormAgent` - interaction with LLM and form data processing
- `SessionManager` - session management and state persistence

### Data Models

- `BaseFormModel` - base class for all form models
- `FormData` - container for form data and metadata
- `SessionInfo` - wrapper for user_form and metadata
- `FormMetadata` - tracking progress, messages, language, etc.
- `System` - system configuration and session parameters
- `AnalyticsResult` - analysis results for the completed form

### LLM Providers

- `OpenRouterProvider` - provider for OpenRouter LLM API
- `LLMResponse` - wrapper for LLM responses with simplified access

### Utilities

- `logging_config` - logging configuration
- `text_sanitizer` - cleaning text from potentially dangerous code
- `model_factory` - creation of model instances
- `schema_utils` - working with JSON schemas
- `helper` - utilities for data presentation

## Usage Example

```python
from pydantic import Field
from pydantic3.agents import FormProcessor, BaseFormModel
from typing import List

# Define nested models
class ContactInfo(BaseModel):
    """Contact information."""
    email: str = Field(default="", description="Email contact")
    phone: str = Field(default="", description="Phone number")
    website: str = Field(default="", description="Website")

class MarketInfo(BaseModel):
    """Market information."""
    size: str = Field(default="", description="Market size")
    growth_rate: float = Field(default=0.0, description="Market growth rate in %")
    competitors: List[str] = Field(default_factory=list, description="List of competitors")

# Define form model
class StartupForm(BaseFormModel):
    name: str = Field(default="", description="Startup name")
    description: str = Field(default="", description="Product/service description")
    industry: str = Field(default="", description="Industry/sector")
    problem_statement: str = Field(default="", description="Problem that the startup solves")
    market: MarketInfo = Field(default_factory=MarketInfo, description="Market information")
    contact: ContactInfo = Field(default_factory=ContactInfo, description="Contact information")

# Initialize processor
processor = FormProcessor(
    form_class=StartupForm,
    api_key="your-api-key",
    role_prompt="Speak with the user in English",
    model_name="openai/gpt-4o-2024-11-20-mini",
    completion_threshold=80
)

# Start session
session_id = await processor.start_session("user-id")

# Process messages
form_data = await processor.process_message("Hi, I have a startup called TechWave", session_id)
print(form_data.session_info.metadata.next_message_ai)
print(f"Progress: {form_data.session_info.metadata.progress}%")

# Get analytics after completion
if form_data.analytics:
    print(f"Data analysis: {form_data.analytics.data_summary}")
```

## Advantages

- Clean architecture with separation of concerns
- Direct LLM calls without complex agent frameworks
- Robust error handling and validation
- Asynchronous API for all major operations
- State persistence in SQLite database
- Full support for Pydantic v2 with proper serialization of nested models

## Technical Notes

### Pydantic v2 Serialization

The framework properly handles nested Pydantic models using the `mode="json"` parameter in `model_dump()` calls:

```python
# Proper serialization of nested models
@field_serializer('user_form')
def serialize_user_form(self, v: BaseModel):
    """Ensure proper serialization of user_form"""
    if hasattr(v, "model_dump"):
        return v.model_dump(mode="json")
    return v
```

### Robust Error Handling

The framework implements comprehensive error handling for serialization operations:

```python
try:
    user_form_data = form_data.session_info.user_form.model_dump(mode="json")
    metadata_data = form_data.session_info.metadata.model_dump(mode="json")
except Exception as e:
    logger.error(f"Agent: Error serializing user_form or metadata: {e}")
    user_form_data = {}
    metadata_data = {}
```

### Persistence Layer

The SessionManager handles persistence using a SQLite database, saving form states as JSON with proper serialization.
