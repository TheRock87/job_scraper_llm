# Form Generation System

This module implements an AI-powered form generation system that helps create complex, multi-level form structures based on business requirements. The system uses LLM (Large Language Models) to generate both the high-level form structure and detailed field definitions.

## Architecture Overview

The form generation system is composed of several components that work together:

1. **FormWizard**: Main entry point that guides users through collecting requirements
2. **FormGenerator**: Creates complete form structures in a single request, including all form details and relations
3. **Models**: Pydantic models that define the input and output data structures

## Components

### FormWizard

The `FormWizard` class serves as a conversational interface for collecting business requirements. It:

- Uses `FormProcessor` to handle the conversation flow
- Collects information about the business, its goals, and form requirements
- Monitors form completion progress
- Triggers form structure generation when the form reaches 100% completion
- Passes the collected data to `FormGenerator` to create the complete form structure

### FormGenerator

The `FormGenerator` creates the complete form structure in a single request:

- Takes a `FormIntentRequest` object containing all the collected business data and settings
- Generates a comprehensive form structure including document metadata, form definitions, and field details
- Ensures proper relationships between forms (root form to subforms)
- Handles field settings and options based on field types
- Supports multiple languages for form generation (en, ru, es, fr)

## Data Models

The system uses several Pydantic models:

### Input Models

1. **FormIntentRequest**: Contains all the data needed to generate a form structure:
   - `data`: Business information and goals
   - `document`: Settings for the document
   - `bot`: Configuration for the assistant bot
   - `notes`: Additional information

2. **DataRequest**: Main data container for business information:
   - `business`: Information about the business (description, website, contact details, etc.)
   - `business_goals`: Goals that the business wants to achieve with the form

3. **BusinessInfo**: Details about the business:
   - `description`: Brief description of the business or product
   - `website`: Business website URL
   - `email`: Contact email
   - `phone`: Contact phone number
   - `industry`: Business industry (e.g., Healthcare, Fintech)
   - `type`: Type of customer interaction (b2b, b2c, internal, custom)

4. **BusinessGoals**: Goals the business wants to achieve:
   - `goals`: List of main goals related to the form (1-3 items)

### Output Models

1. **CompleteFormStructure**: Contains the complete generated form structure:
   - `document`: Document metadata (title, description)
   - `explanation`: Brief explanation of the overall structure
   - `forms`: List of form definitions with detailed field definitions

2. **FormDetail**: Contains detailed form definition:
   - `name`: Unique identifier for the form
   - `title`: Display title for the form
   - `description`: Description of the form's purpose
   - `is_root_form`: Whether this is the root form
   - `fields`: List of field definitions

3. **FormField**: Definition of a form field:
   - `name`: Unique identifier for the field
   - `title`: Display title for the field
   - `description`: Description of the field
   - `type`: Field type (text, number, select, etc.)
   - `required`: Whether the field is required
   - `order`: Numerical order of appearance
   - `settings`: Additional settings specific to the field type
   - `relation`: For relation fields, contains the relationship definition

4. **RelationField**: Defines a relationship between forms:
   - `target_form`: ID of the target form being referenced
   - `is_multiple`: Whether the relationship can reference multiple instances

5. **SelectOption**: Defines an option for select and multiselect fields:
   - `label`: Display label for the option in the specified language
   - `value`: Unique identifier for the option in English snake_case

### Testing Model

The `TestFormIntentRequest` model is specifically designed for testing and development:

```python
class TestFormIntentRequest(BaseModel):
    """Testing form model with all fields made optional for dynamic filling by LLM."""

    data: DataRequest
    document: Optional[Dict[str, Any]] = Field(default_factory=dict)
    bot: Optional[Dict[str, Any]] = Field(default_factory=dict)
    notes: Optional[str] = None
```

This model allows for dynamic filling through the conversation with LLM while maintaining the expected structure.

## Workflow

1. **User Interaction**:
   - User interacts with the `FormWizard` through a conversational interface
   - System collects information about business, goals, and form requirements
   - The conversation continues until all necessary information is collected

2. **Form Structure Generation**:
   - When the form reaches 100% completion, `generate_form_structure` is triggered
   - A `FormGenerator` instance is created with the collected `FormIntentRequest` data
   - The generator produces a complete form structure in a single request

3. **Language Support**:
   - The system supports multiple languages for form generation (en, ru, es, fr)
   - All text, titles, descriptions, and option labels are generated in the specified language
   - Field names and option values remain in English for technical compatibility

4. **Field Settings Processing**:
   - Each field type has specific settings processed by the `_ensure_field_settings` method
   - Select/multiselect fields have options normalized to include both label and value
   - Relations between forms are properly structured and validated

## Example Usage

```python
# Create a FormWizard instance
wizard = FormWizard.from_env()

# Start a session
session_id = await wizard.start_session()

# Process user messages until form is complete
response = await wizard.process_message("I need a form for user feedback")
# ... more messages ...

# When form is complete, generate the form structure
form_intent = FormIntentRequest(**collected_data)
generator = FormGenerator(
    form_intent=form_intent,
    api_key=api_key,
    language="en"  # or "ru", "es", "fr"
)
complete_structure = await generator.generate_complete_structure()
```

## Testing

The system includes a comprehensive test file:

**form_generator_test.py**: Tests the form structure generation with interactive language selection

The test file demonstrates proper usage and can be used to validate functionality with different languages.

## Generated Form Structure

The final output is a nested JSON structure with:

- Document metadata (title, description)
- List of forms with their detailed definitions
- Each form contains:
  - Basic properties (name, title, description)
  - List of fields with complete definitions
  - For select/multiselect fields, options with label and value
  - For relation fields, proper references to other forms
- An explanation of the overall form structure

The structure ensures that:
1. The root form contains relation fields to all subforms
2. Subforms do not contain relation fields back to the root form
3. All relationships flow only from the root form to subforms
