"""
Form processing framework with improved model structure.

This implementation has two main models:
1. Form model - for representing and manipulating form data
2. Analytics model - for generating insights based on completed forms
"""

from .core.processor import FormProcessor
from .models.form import BaseFormModel, FormData, FormMetadata
from .models.analytics import AnalyticsResult

__all__ = [
    "FormProcessor",
    "BaseFormModel",
    "FormData",
    "FormMetadata",
    "AnalyticsResult"
]
