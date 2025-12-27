"""
Intermediate format definitions.

These dataclasses represent the normalized schema used between
the parse and generate stages.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PropertyDef:
    """Definition of a resource property."""

    name: str  # Python name (snake_case)
    original_name: str  # CloudFormation name (PascalCase)
    type: str  # Python type string
    required: bool = False
    documentation: str = ""
    nested_type: str | None = None  # For object types
    enum_type: str | None = None  # For enum types
    is_list: bool = False
    is_map: bool = False
    item_type: str | None = None  # For list/map item types
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class AttributeDef:
    """Definition of a resource attribute (GetAtt target)."""

    name: str
    type: str = "str"
    documentation: str = ""


@dataclass
class ResourceDef:
    """Definition of a CloudFormation resource type."""

    name: str  # Python class name
    service: str  # Service name (e.g., "s3")
    full_type: str  # Full CF type (e.g., "AWS::S3::Bucket")
    documentation: str = ""
    properties: list[PropertyDef] = field(default_factory=list)
    attributes: list[AttributeDef] = field(default_factory=list)


@dataclass
class EnumDef:
    """Definition of an enumeration type."""

    name: str
    service: str
    values: list[str] = field(default_factory=list)
    documentation: str = ""


@dataclass
class NestedTypeDef:
    """Definition of a nested property type."""

    name: str  # Python class name
    service: str
    original_name: str  # CloudFormation property type name
    properties: list[PropertyDef] = field(default_factory=list)
    documentation: str = ""


@dataclass
class IntermediateSchema:
    """The complete intermediate schema for code generation."""

    schema_version: str
    domain: str
    generated_at: str
    cf_spec_version: str = ""
    botocore_version: str = ""
    resources: list[ResourceDef] = field(default_factory=list)
    enums: list[EnumDef] = field(default_factory=list)
    nested_types: list[NestedTypeDef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "schema_version": self.schema_version,
            "domain": self.domain,
            "generated_at": self.generated_at,
            "cf_spec_version": self.cf_spec_version,
            "botocore_version": self.botocore_version,
            "resources": [self._resource_to_dict(r) for r in self.resources],
            "enums": [self._enum_to_dict(e) for e in self.enums],
            "nested_types": [self._nested_to_dict(n) for n in self.nested_types],
        }

    def _resource_to_dict(self, r: ResourceDef) -> dict:
        return {
            "name": r.name,
            "service": r.service,
            "full_type": r.full_type,
            "documentation": r.documentation,
            "properties": [self._prop_to_dict(p) for p in r.properties],
            "attributes": [
                {"name": a.name, "type": a.type, "documentation": a.documentation}
                for a in r.attributes
            ],
        }

    def _prop_to_dict(self, p: PropertyDef) -> dict:
        return {
            "name": p.name,
            "original_name": p.original_name,
            "type": p.type,
            "required": p.required,
            "documentation": p.documentation,
            "nested_type": p.nested_type,
            "enum_type": p.enum_type,
            "is_list": p.is_list,
            "is_map": p.is_map,
            "item_type": p.item_type,
            "constraints": p.constraints,
        }

    def _enum_to_dict(self, e: EnumDef) -> dict:
        return {
            "name": e.name,
            "service": e.service,
            "values": e.values,
            "documentation": e.documentation,
        }

    def _nested_to_dict(self, n: NestedTypeDef) -> dict:
        return {
            "name": n.name,
            "service": n.service,
            "original_name": n.original_name,
            "properties": [self._prop_to_dict(p) for p in n.properties],
            "documentation": n.documentation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IntermediateSchema":
        """Load from JSON dict."""
        schema = cls(
            schema_version=data["schema_version"],
            domain=data["domain"],
            generated_at=data["generated_at"],
            cf_spec_version=data.get("cf_spec_version", ""),
            botocore_version=data.get("botocore_version", ""),
        )

        for r in data.get("resources", []):
            schema.resources.append(
                ResourceDef(
                    name=r["name"],
                    service=r["service"],
                    full_type=r["full_type"],
                    documentation=r.get("documentation", ""),
                    properties=[
                        cls._prop_from_dict(p) for p in r.get("properties", [])
                    ],
                    attributes=[AttributeDef(**a) for a in r.get("attributes", [])],
                )
            )

        for e in data.get("enums", []):
            schema.enums.append(EnumDef(**e))

        for n in data.get("nested_types", []):
            schema.nested_types.append(
                NestedTypeDef(
                    name=n["name"],
                    service=n["service"],
                    original_name=n.get("original_name", n["name"]),
                    properties=[
                        cls._prop_from_dict(p) for p in n.get("properties", [])
                    ],
                    documentation=n.get("documentation", ""),
                )
            )

        return schema

    @staticmethod
    def _prop_from_dict(p: dict) -> PropertyDef:
        return PropertyDef(
            name=p["name"],
            original_name=p["original_name"],
            type=p["type"],
            required=p.get("required", False),
            documentation=p.get("documentation", ""),
            nested_type=p.get("nested_type"),
            enum_type=p.get("enum_type"),
            is_list=p.get("is_list", False),
            is_map=p.get("is_map", False),
            item_type=p.get("item_type"),
            constraints=p.get("constraints", {}),
        )
