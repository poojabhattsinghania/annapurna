"""
Data Validation Service for Recipe Quality Assurance

This service validates recipe data to ensure quality and completeness.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "error"  # Blocking issues
    WARNING = "warning"  # Quality issues
    INFO = "info"  # Suggestions


@dataclass
class ValidationIssue:
    """Represents a data validation issue"""
    field: str
    severity: ValidationSeverity
    message: str


class RecipeDataValidator:
    """Validates recipe data quality"""

    # Required fields
    REQUIRED_FIELDS = ["title", "source_url", "recipe_creator_name"]

    # Minimum lengths
    MIN_TITLE_LENGTH = 3
    MAX_TITLE_LENGTH = 200
    MIN_DESCRIPTION_LENGTH = 20
    MIN_INGREDIENTS_COUNT = 2
    MIN_INSTRUCTIONS_COUNT = 2

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate_recipe(self, recipe_data: Dict) -> tuple[bool, List[ValidationIssue]]:
        """
        Validate complete recipe data

        Args:
            recipe_data: Dictionary containing recipe data

        Returns:
            (is_valid, issues) tuple
        """
        self.issues = []

        # Required fields check
        self._validate_required_fields(recipe_data)

        # Title validation
        self._validate_title(recipe_data.get("title"))

        # Description validation
        self._validate_description(recipe_data.get("description"))

        # Ingredients validation
        self._validate_ingredients(recipe_data.get("ingredients", []))

        # Instructions validation
        self._validate_instructions(recipe_data.get("instructions", []))

        # Timing validation
        self._validate_timings(recipe_data)

        # URL validation
        self._validate_url(recipe_data.get("source_url"))

        # Check if there are any ERROR severity issues
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

        return (not has_errors, self.issues)

    def _validate_required_fields(self, recipe_data: Dict):
        """Validate that all required fields are present"""
        for field in self.REQUIRED_FIELDS:
            if not recipe_data.get(field):
                self.issues.append(ValidationIssue(
                    field=field,
                    severity=ValidationSeverity.ERROR,
                    message=f"Required field '{field}' is missing"
                ))

    def _validate_title(self, title: Optional[str]):
        """Validate recipe title"""
        if not title:
            return  # Already caught by required fields

        if len(title) < self.MIN_TITLE_LENGTH:
            self.issues.append(ValidationIssue(
                field="title",
                severity=ValidationSeverity.ERROR,
                message=f"Title too short (min {self.MIN_TITLE_LENGTH} characters)"
            ))

        if len(title) > self.MAX_TITLE_LENGTH:
            self.issues.append(ValidationIssue(
                field="title",
                severity=ValidationSeverity.WARNING,
                message=f"Title too long (max {self.MAX_TITLE_LENGTH} characters recommended)"
            ))

        # Check for common spam patterns
        spam_keywords = ["click here", "buy now", "limited offer"]
        if any(keyword in title.lower() for keyword in spam_keywords):
            self.issues.append(ValidationIssue(
                field="title",
                severity=ValidationSeverity.ERROR,
                message="Title contains spam keywords"
            ))

    def _validate_description(self, description: Optional[str]):
        """Validate recipe description"""
        if not description:
            self.issues.append(ValidationIssue(
                field="description",
                severity=ValidationSeverity.WARNING,
                message="Description is missing"
            ))
            return

        if len(description) < self.MIN_DESCRIPTION_LENGTH:
            self.issues.append(ValidationIssue(
                field="description",
                severity=ValidationSeverity.WARNING,
                message=f"Description too short (min {self.MIN_DESCRIPTION_LENGTH} characters recommended)"
            ))

    def _validate_ingredients(self, ingredients: List[Dict]):
        """Validate ingredients list"""
        if not ingredients:
            self.issues.append(ValidationIssue(
                field="ingredients",
                severity=ValidationSeverity.ERROR,
                message="Recipe must have at least one ingredient"
            ))
            return

        if len(ingredients) < self.MIN_INGREDIENTS_COUNT:
            self.issues.append(ValidationIssue(
                field="ingredients",
                severity=ValidationSeverity.WARNING,
                message=f"Very few ingredients (min {self.MIN_INGREDIENTS_COUNT} recommended)"
            ))

        # Check for ingredient quality
        for i, ingredient in enumerate(ingredients):
            if not ingredient.get("standard_name") and not ingredient.get("item"):
                self.issues.append(ValidationIssue(
                    field=f"ingredients[{i}]",
                    severity=ValidationSeverity.WARNING,
                    message="Ingredient missing name"
                ))

            # Check for reasonable quantities
            if ingredient.get("quantity"):
                try:
                    qty = float(ingredient["quantity"])
                    if qty <= 0:
                        self.issues.append(ValidationIssue(
                            field=f"ingredients[{i}].quantity",
                            severity=ValidationSeverity.WARNING,
                            message="Ingredient quantity must be positive"
                        ))
                    if qty > 10000:
                        self.issues.append(ValidationIssue(
                            field=f"ingredients[{i}].quantity",
                            severity=ValidationSeverity.WARNING,
                            message="Ingredient quantity seems unreasonably large"
                        ))
                except (ValueError, TypeError):
                    pass

    def _validate_instructions(self, instructions: List[Dict]):
        """Validate cooking instructions"""
        if not instructions:
            self.issues.append(ValidationIssue(
                field="instructions",
                severity=ValidationSeverity.ERROR,
                message="Recipe must have at least one instruction step"
            ))
            return

        if len(instructions) < self.MIN_INSTRUCTIONS_COUNT:
            self.issues.append(ValidationIssue(
                field="instructions",
                severity=ValidationSeverity.WARNING,
                message=f"Very few instruction steps (min {self.MIN_INSTRUCTIONS_COUNT} recommended)"
            ))

        # Check instruction quality
        for i, instruction in enumerate(instructions):
            step_text = instruction.get("instruction", "")
            if not step_text or len(step_text.strip()) < 10:
                self.issues.append(ValidationIssue(
                    field=f"instructions[{i}]",
                    severity=ValidationSeverity.WARNING,
                    message="Instruction step is too short or empty"
                ))

    def _validate_timings(self, recipe_data: Dict):
        """Validate prep time, cook time, and total time"""
        prep_time = recipe_data.get("prep_time_minutes")
        cook_time = recipe_data.get("cook_time_minutes")
        total_time = recipe_data.get("total_time_minutes")

        # Check for reasonable time values
        for time_field, time_value in [
            ("prep_time_minutes", prep_time),
            ("cook_time_minutes", cook_time),
            ("total_time_minutes", total_time)
        ]:
            if time_value is not None:
                try:
                    time_int = int(time_value)
                    if time_int < 0:
                        self.issues.append(ValidationIssue(
                            field=time_field,
                            severity=ValidationSeverity.WARNING,
                            message="Time cannot be negative"
                        ))
                    if time_int > 1440:  # More than 24 hours
                        self.issues.append(ValidationIssue(
                            field=time_field,
                            severity=ValidationSeverity.WARNING,
                            message="Time seems unreasonably long (>24 hours)"
                        ))
                except (ValueError, TypeError):
                    pass

        # Validate total time logic
        if prep_time and cook_time and total_time:
            try:
                if int(total_time) < (int(prep_time) + int(cook_time)):
                    self.issues.append(ValidationIssue(
                        field="total_time_minutes",
                        severity=ValidationSeverity.WARNING,
                        message="Total time is less than prep + cook time"
                    ))
            except (ValueError, TypeError):
                pass

    def _validate_url(self, url: Optional[str]):
        """Validate source URL"""
        if not url:
            return  # Already caught by required fields

        if not url.startswith(("http://", "https://")):
            self.issues.append(ValidationIssue(
                field="source_url",
                severity=ValidationSeverity.ERROR,
                message="URL must start with http:// or https://"
            ))

        # Check URL length
        if len(url) > 2048:
            self.issues.append(ValidationIssue(
                field="source_url",
                severity=ValidationSeverity.WARNING,
                message="URL is unusually long"
            ))


def validate_recipe(recipe_data: Dict) -> tuple[bool, List[ValidationIssue]]:
    """
    Convenience function to validate recipe data

    Returns:
        (is_valid, issues) tuple
    """
    validator = RecipeDataValidator()
    return validator.validate_recipe(recipe_data)
