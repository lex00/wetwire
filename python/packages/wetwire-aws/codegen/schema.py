"""
Intermediate schema definitions for codegen pipeline.

Contains dataclasses for representing parsed CloudFormation resources
and utilities for name transformations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Python reserved keywords that need escaping
PYTHON_KEYWORDS: dict[str, str] = {
    # Keywords that conflict with Python builtins/keywords
    "and": "and_",
    "as": "as_",
    "assert": "assert_",
    "async": "async_",
    "await": "await_",
    "break": "break_",
    "class": "class_",
    "continue": "continue_",
    "def": "def_",
    "del": "del_",
    "elif": "elif_",
    "else": "else_",
    "except": "except_",
    "False": "false_",
    "finally": "finally_",
    "for": "for_",
    "from": "from_",
    "global": "global_",
    "if": "if_",
    "import": "import_",
    "in": "in_",
    "is": "is_",
    "lambda": "lambda_",
    "None": "none_",
    "nonlocal": "nonlocal_",
    "not": "not_",
    "or": "or_",
    "pass": "pass_",
    "raise": "raise_",
    "return": "return_",
    "True": "true_",
    "try": "try_",
    "type": "type_",
    "while": "while_",
    "with": "with_",
    "yield": "yield_",
}


def escape_python_keyword(name: str) -> str:
    """Escape Python reserved keywords by appending underscore."""
    return PYTHON_KEYWORDS.get(name, name)


def to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case."""
    # Handle consecutive capitals (e.g., EC2Fleet -> ec2_fleet)
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    result = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    return escape_python_keyword(result)


@dataclass
class PropertyDef:
    """Definition of a resource property."""

    name: str
    original_name: str
    type: str
    required: bool = False
    documentation: str = ""
    nested_type: str | None = None
    is_list: bool = False
    is_map: bool = False
    item_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "original_name": self.original_name,
            "type": self.type,
            "required": self.required,
            "documentation": self.documentation,
            "nested_type": self.nested_type,
            "is_list": self.is_list,
            "is_map": self.is_map,
            "item_type": self.item_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PropertyDef:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            original_name=data["original_name"],
            type=data["type"],
            required=data.get("required", False),
            documentation=data.get("documentation", ""),
            nested_type=data.get("nested_type"),
            is_list=data.get("is_list", False),
            is_map=data.get("is_map", False),
            item_type=data.get("item_type"),
        )


@dataclass
class AttributeDef:
    """Definition of a resource attribute (GetAtt)."""

    name: str
    type: str = "str"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"name": self.name, "type": self.type}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttributeDef:
        """Create from dictionary."""
        return cls(name=data["name"], type=data.get("type", "str"))


@dataclass
class ResourceDef:
    """Definition of a CloudFormation resource type."""

    name: str
    service: str
    full_type: str
    documentation: str = ""
    properties: list[PropertyDef] = field(default_factory=list)
    attributes: list[AttributeDef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "service": self.service,
            "full_type": self.full_type,
            "documentation": self.documentation,
            "properties": [p.to_dict() for p in self.properties],
            "attributes": [a.to_dict() for a in self.attributes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResourceDef:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            service=data["service"],
            full_type=data["full_type"],
            documentation=data.get("documentation", ""),
            properties=[PropertyDef.from_dict(p) for p in data.get("properties", [])],
            attributes=[AttributeDef.from_dict(a) for a in data.get("attributes", [])],
        )


@dataclass
class NestedTypeDef:
    """Definition of a nested property type."""

    name: str
    service: str
    original_name: str
    properties: list[PropertyDef] = field(default_factory=list)
    documentation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "service": self.service,
            "original_name": self.original_name,
            "properties": [p.to_dict() for p in self.properties],
            "documentation": self.documentation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NestedTypeDef:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            service=data["service"],
            original_name=data["original_name"],
            properties=[PropertyDef.from_dict(p) for p in data.get("properties", [])],
            documentation=data.get("documentation", ""),
        )


@dataclass
class IntermediateSchema:
    """Intermediate representation of parsed CloudFormation spec."""

    schema_version: str
    domain: str
    generated_at: str
    source_version: str = ""
    sdk_version: str = ""
    resources: list[ResourceDef] = field(default_factory=list)
    nested_types: list[NestedTypeDef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schema_version": self.schema_version,
            "domain": self.domain,
            "generated_at": self.generated_at,
            "source_version": self.source_version,
            "sdk_version": self.sdk_version,
            "resources": [r.to_dict() for r in self.resources],
            "nested_types": [n.to_dict() for n in self.nested_types],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntermediateSchema:
        """Create from dictionary."""
        return cls(
            schema_version=data["schema_version"],
            domain=data["domain"],
            generated_at=data["generated_at"],
            source_version=data.get("source_version", ""),
            sdk_version=data.get("sdk_version", ""),
            resources=[ResourceDef.from_dict(r) for r in data.get("resources", [])],
            nested_types=[NestedTypeDef.from_dict(n) for n in data.get("nested_types", [])],
        )


def python_type_for_property(prop: PropertyDef) -> str:
    """Get the Python type annotation for a property."""
    base_type = prop.type

    # Handle list types
    if prop.is_list:
        if prop.nested_type:
            return f"list[{prop.nested_type}]"
        elif prop.item_type:
            return f"list[{prop.item_type}]"
        else:
            return "list[Any]"

    # Handle map types
    if prop.is_map:
        if prop.nested_type:
            return f"dict[str, {prop.nested_type}]"
        elif prop.item_type:
            return f"dict[str, {prop.item_type}]"
        else:
            return "dict[str, Any]"

    # Handle nested types
    if prop.nested_type:
        return prop.nested_type

    return base_type


def format_file(content: str) -> str:
    """Format Python source code (placeholder - actual formatting done by black)."""
    return content
