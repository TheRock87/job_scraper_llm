from typing import Type, TypeVar, cast
from pydantic import BaseModel
from polyfactory.factories.pydantic_factory import ModelFactory
from faker import Faker

T = TypeVar("T", bound=BaseModel)


class UniversalModelFactory:
    """Factory for generating Pydantic models with or without fake data."""

    def __init__(self, model: Type[T], fill_data: bool = False):
        if not issubclass(model, BaseModel):
            raise ValueError("Provided model must be a subclass of Pydantic BaseModel")

        self.model = model
        self.fill_data = fill_data
        self.factory = self._create_factory()

    def _create_factory(self):
        """Dynamically creates a factory for the given model."""
        faker_instance = Faker("en_US")
        faker_instance.seed_instance(42)  # Ensures reproducibility

        class DynamicFactory(ModelFactory[self.model]):  # ✅ ПРАВИЛЬНО
            __model__ = self.model
            __faker__ = faker_instance

        return DynamicFactory()  # Создаём экземпляр фабрики

    def _clear_data(self, data: dict, model_cls: Type[BaseModel]) -> dict:
        """Recursively replaces values with empty equivalents.

        Also handles nested models by creating proper empty nested structure
        with all required fields initialized as empty.
        """
        cleared_data = {}

        # First pass: get all field types from the model
        field_types = {}
        if hasattr(model_cls, "model_fields"):
            field_types = {
                field_name: field_info.annotation
                for field_name, field_info in model_cls.model_fields.items()
            }

        # Second pass: process the data with field type info
        for key, value in data.items():
            field_type = field_types.get(key)

            if isinstance(value, str):
                cleared_data[key] = ""
            elif isinstance(value, list):
                cleared_data[key] = []
            elif isinstance(value, dict):
                # If this is a nested model, ensure we create a valid empty structure
                if field_type and hasattr(field_type, "model_fields"):
                    nested_model = field_type
                    # Create an empty structure for the nested model
                    cleared_data[key] = self._clear_data(value, nested_model)
                else:
                    cleared_data[key] = {}
            elif value is None:
                cleared_data[key] = None
            else:
                # For numbers, booleans, etc.
                # Try to find a default/zero value appropriate for the type
                if isinstance(value, int):
                    cleared_data[key] = 0
                elif isinstance(value, float):
                    cleared_data[key] = 0.0
                elif isinstance(value, bool):
                    cleared_data[key] = False
                else:
                    cleared_data[key] = value

        return cleared_data

    def build(self) -> T:
        """Creates a model instance with fake or empty data."""
        instance = self.factory.build()
        if not self.fill_data:
            # Use model_construct to bypass validation
            # This is crucial when working with partially filled forms
            cleared_data = self._clear_data(instance.model_dump(), self.model)
            return cast(T, self.model.model_construct(**cleared_data))
        return cast(T, instance)


if __name__ == "__main__":
    class Address(BaseModel):
        city: str
        street: str

    class User(BaseModel):
        id: int
        email: str
        name: str
        address: Address

    user_with_data = UniversalModelFactory(User, fill_data=True).build()
    print(f"Filled model: {user_with_data}")

    empty_user = UniversalModelFactory(User, fill_data=False).build()
    print(f"Empty model: {empty_user}")
