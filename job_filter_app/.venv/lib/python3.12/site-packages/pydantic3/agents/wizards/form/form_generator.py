from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import yaml

from ....utils import LogConsole, SimpleLogger
from ...providers.openrouter import OpenRouterProvider
from .models import SetupRequest


class Document(BaseModel):
    title: str = Field(description="Title of the document in [LANGUAGE]")
    description: str = Field(description="Description of the document in [LANGUAGE]")


class RelationField(BaseModel):
    """Definition of a relationship between forms."""
    target_form: str = Field(description="ID of the target form being referenced")
    is_multiple: bool = Field(default=False, description="Whether the relationship can reference multiple instances")


class SelectOption(BaseModel):
    """Option for select and multiselect fields."""
    label: str = Field(description="Display label for the option in the [LANGUAGE]")
    value: str = Field(description="Unique identifier for the option (English, camel_case)")


class FormField(BaseModel):
    """Definition of a form field."""
    name: str = Field(description="Unique identifier for the field (snake_case) in [LANGUAGE]")
    title: str = Field(description="Display title for the field (human-readable) in [LANGUAGE]")
    description: str = Field(description="Helpful description text in [LANGUAGE]")
    type: str = Field(description="Field type (text, number, date, etc.) in English")
    required: bool = Field(description="Whether the field is required")
    order: int = Field(description="Numerical order of appearance")
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional settings (options for select, target_form for relation, etc.)"
    )
    relation: Optional[RelationField] = Field(
        default=None,
        description="Relation field to another form"
    )


class FormDetail(BaseModel):
    """Response format for detailed form definition."""
    name: str = Field(description="Unique name identifier for the form")
    title: str = Field(description="Display title for the form")
    description: str = Field(description="Description of the form's purpose")
    is_root_form: bool = Field(description="Whether this is the root form")
    fields: List[Dict[str, Any]] = Field(
        description="List of fields in this form with complete definitions"
    )


class CompleteFormStructure(BaseModel):
    """Complete form structure including document metadata, forms, and explanation."""
    document: Document = Field(description="Document metadata including title and description")
    explanation: str = Field(description="Brief explanation of the overall form structure and how it meets the business goals")
    forms: List[FormDetail] = Field(description="List of form definitions with complete field details")


class FormGenerator:
    """Single-request form generator that creates complete form structures."""

    def __init__(self, setup_data: Dict[str, Any], model_name: str = "openai/gpt-4o-2024-11-20", api_key: Optional[str] = None, language: str = "en"):

        self.model_name = model_name
        self.api_key = api_key
        self.language = language
        self.logger = SimpleLogger("form_generator")
        self.console = LogConsole(name="form_generator")

        self.setup_data = setup_data

        # try:
        #     self.form_data = SetupRequest.model_validate(data, strict=False)
        # except Exception as e:
        #     self.logger.error(f"Error parsing SetupRequest: {str(e)}")
        #     raise ValueError(f"Failed to parse data request: {str(e)}")

        if not api_key:
            self.logger.warning("No API key provided, will use environment variable")

    def create_provider(self) -> OpenRouterProvider:
        """Create a new OpenRouter provider instance."""
        return OpenRouterProvider(
            api_key=self.api_key,
            model_name=self.model_name,
        )

    @staticmethod
    def _make_block(tag: str, data: str) -> str:
        tag = tag.upper()
        return f"[{tag}] {data} [/{tag}]"

    def _trim(self, text: str) -> str:
        """Trim lines and remove extra spaces."""
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())

    async def generate_complete_structure(self) -> CompleteFormStructure:
        """Generate complete form structure in a single request."""
        provider = self.create_provider()

        system_message = f"""
        You are an expert form designer AI assistant that creates comprehensive form structures for businesses. All text, titles, descriptions, and option labels should be in {self.language}. Options must include both label (in {self.language}) and value (in English snake_case). Always use lowercase for field types. Field relationships should only flow from root form to subforms.
        """
        system_message = self._trim(system_message)

        # Prompt blocks
        prompt_blocks_str = "\n".join([
            self._make_block("ABOUT_BUSINESS", yaml.dump(self.setup_data)),
            self._make_block("USER_LANGUAGE", self.language),
            self._make_block("SCHEMA", CompleteFormStructure.model_json_schema()),
        ])

        prompt_extra = f"""
        Create a complete form structure for a business application in a single request.

        ### Language instructions:
        - All titles, descriptions, and labels should be in [USER_LANGUAGE]
        - Field names should be in English snake_case
        - For select/multiselect options, use [USER_LANGUAGE] for both labels and values (in snake_case)
        - Form explanations should be written in [USER_LANGUAGE]

        ## TASK
        Create a logical hierarchy of forms to achieve these business goals. Think carefully about how to organize this into a root form and necessary subforms.

        ## IMPORTANT REQUIREMENTS
        1. The root form MUST contain RELATION fields to all subforms
        2. Subforms should NOT contain RELATION fields back to the root form or other forms
        3. All relationships should flow only from the root form to subforms, not the other way around
        4. The root form serves as the central hub connecting to all other forms
        5. Root form should have minimum one not relation field

        ## AVAILABLE FIELD TYPES
        - text: For free text input
        - number: For numerical values
        - date: For date selection
        - time: For time selection
        - boolean: For yes/no questions
        - select: For single option from a list
        - multiselect: For multiple options from a list
        - formula: For calculated fields
        - email: For email addresses
        - phone: For phone numbers
        - url: For web addresses
        - currency: For monetary values
        - relation: For linking to another form (ONLY USE IN ROOT FORM)

        ## SELECT/MULTISELECT FIELDS INSTRUCTIONS
        For select and multiselect fields, you MUST provide options in the following format:
        ```
        "options": [
        {{
            "label": "Option label in the specified language",
            "value": "option_value_in_english_snake_case"
        }},
        ...
        ]
        ```
        Where:
        - "label" is the human-readable option text in {self.language}
        - "value" is a unique identifier in English using snake_case

        ## RELATION FIELDS INSTRUCTIONS
        When creating relation type fields (only in the root form), you MUST include:
        1. "type": "relation" to identify it as a relationship field
        2. A "relation" object containing:
        - "target_form": The name of the target form being referenced (required)
        - "is_multiple": Always set to false

        ## FORM REQUIREMENTS
        For each form, include:
        1. Basic properties (name, title, description) with text in {self.language}
        2. Whether it's the root form (is_root_form: true/false) - only one form can be root
        3. Proper fields for data collection based on the business needs
        4. relation fields ONLY in the root form, pointing to each subform

        ## OUTPUT REQUIREMENTS
        Provide a complete form structure including:
        1. Document metadata (title and description) in {self.language}
        2. A list of forms with their names, titles, descriptions, and complete field definitions
        3. An explanation of the overall form structure
        4. Ensure the root form contains relation fields to all other forms
        5. Ensure subforms do NOT contain relation fields back to the root form

        For each field, include all attributes:
        - name: A unique identifier (snake_case in English)
        - title: Display title in {self.language}
        - description: Helpful description text in {self.language}
        - type: One of the field types above (always in lowercase)
        - required: true/false
        - order: Numerical order of appearance
        - settings: Additional settings specific to the field type
        - relation: For relation type fields (in root form only), include an object with target_form and is_multiple properties

        Return a valid JSON object based on the following [SCHEMA]!
        """

        prompt = prompt_blocks_str + "\n\n---\n\n" + self._trim(prompt_extra)

        # Generate response using the OpenRouter provider
        response_json = await provider.json_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.2
        )

        # Process the response to ensure proper relationship structure
        if "forms" in response_json:
            # Find the root form and non-root forms
            root_form = next((form for form in response_json["forms"] if form.get("is_root_form", False)), None)
            non_root_forms = [form for form in response_json["forms"] if not form.get("is_root_form", False)]

            # If we have a root form and at least one non-root form
            if root_form and non_root_forms:
                # Ensure all field types are lowercase
                for form in response_json["forms"]:
                    for field in form.get("fields", []):
                        if "type" in field and isinstance(field["type"], str):
                            field["type"] = field["type"].lower()

                        # Process fields to ensure proper settings format
                        self._ensure_field_settings(field)

                # Check which subforms are already referenced in relation fields
                existing_relation_targets = set()
                for field in root_form.get("fields", []):
                    if field.get("type") == "relation":
                        if "relation" in field:
                            target_form = field.get("relation", {}).get("target_form")
                            if target_form:
                                existing_relation_targets.add(target_form)
                        # Backward compatibility for older format
                        elif "settings" in field and "target_form" in field["settings"]:
                            # Migrate from old format to new format
                            field["relation"] = {
                                "target_form": field["settings"]["target_form"],
                                "is_multiple": field["settings"].get("is_multiple", False)
                            }
                            existing_relation_targets.add(field["settings"]["target_form"])

                # Find subforms that don't have relations from root form
                missing_relations = []
                for form in non_root_forms:
                    if form["name"] not in existing_relation_targets:
                        missing_relations.append(form)

                # Add missing relation fields to root form
                next_order = max([field.get("order", 0) for field in root_form.get("fields", [])], default=0) + 1
                for form in missing_relations:
                    # Create a new relation field
                    relation_field = {
                        "name": f"{form['name']}_relation",
                        "title": f"Related {form['title']}",
                        "description": f"Link to {form['title']}",
                        "type": "relation",
                        "required": True,
                        "order": next_order,
                        "settings": {},
                        "relation": {
                            "target_form": form["name"],
                            "is_multiple": False
                        }
                    }
                    root_form["fields"].append(relation_field)
                    next_order += 1

                    self.logger.info(f"Added missing relation from root form to {form['name']}")

            # Remove all relation fields from non-root forms
            for form in non_root_forms:
                # Filter out relation type fields
                form["fields"] = [field for field in form.get("fields", []) if field.get("type") != "relation"]
                self.logger.info(f"Removed relation fields from subform: {form['name']}")

        # Convert the JSON response to the CompleteFormStructure model
        try:
            return CompleteFormStructure.model_validate(response_json)
        except Exception as e:
            self.logger.error(f"Error parsing CompleteFormStructure: {str(e)}")
            self.logger.error(f"Response JSON: {response_json}")
            raise ValueError(f"Failed to parse complete form structure: {str(e)}")

    def _ensure_field_settings(self, field: Dict[str, Any]) -> None:
        """
        Adds basic settings for fields based on their type.

        Args:
            field: Field with settings
        """
        field_type = field.get("type", "text")

        # Make sure settings exist
        if "settings" not in field:
            field["settings"] = {}

        # Process select/multiselect fields
        if field_type in ["select", "multiselect"]:
            # Ensure proper options format
            self._ensure_proper_options_format(field)

            # Add basic settings for select/multiselect
            field["settings"]["format"] = field["settings"].get("format", "dropdown")
            field["settings"]["allowClear"] = field["settings"].get("allowClear", True)

        # Basic settings for relation field
        elif field_type == "relation":
            field["settings"]["display_mode"] = field["settings"].get("display_mode", "default")
            field["settings"]["expanded"] = field["settings"].get("expanded", False)

        # Add common settings for all fields
        field["settings"]["placeholder"] = field["settings"].get("placeholder", "")
        field["settings"]["helpText"] = field["settings"].get("helpText", "")

    def _ensure_proper_options_format(self, field: Dict[str, Any]) -> None:
        """Ensure select/multiselect fields have options in the correct format."""
        # Check if field has options in settings
        if "settings" in field and "options" in field["settings"]:
            options = field["settings"]["options"]

            # If options is a list of strings, convert to proper format
            if options and isinstance(options, list) and all(isinstance(option, str) for option in options):
                formatted_options = []
                for option in options:
                    # Convert option to snake_case for value
                    value = self._to_snake_case(option)
                    # Use SelectOption model to validate
                    option_model = SelectOption(label=option, value=value)
                    formatted_options.append(option_model.model_dump())
                field["settings"]["options"] = formatted_options
                self.logger.info(f"Converted options format for field: {field.get('name')}")

            # If options is empty, provide a default set
            elif not options:
                field_name = field.get('name', '')
                default_options = []

                # Create some default options based on field name
                for i in range(1, 4):
                    label = f"Option {i} for {field_name}"
                    value = f"option_{i}_{self._to_snake_case(field_name)}"
                    option_model = SelectOption(label=label, value=value)
                    default_options.append(option_model.model_dump())

                field["settings"]["options"] = default_options
                self.logger.info(f"Added default options for field: {field.get('name')}")

    def _to_snake_case(self, text: str) -> str:
        """Convert a string to snake_case."""
        # First, remove any non-alphanumeric characters except spaces
        import re
        # Convert to lowercase and replace spaces with underscores
        return re.sub(r'[^a-zA-Z0-9\s]', '', text).lower().replace(' ', '_')
