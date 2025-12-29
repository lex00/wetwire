"""Intermediate Representation (IR) for parsed CloudFormation templates.

This module defines the data structures used to represent a CloudFormation
template after parsing but before code generation. The IR provides a
normalized, Python-friendly representation that decouples parsing from
code generation.

The IR classes extend base classes from dataclass-dsl with CloudFormation-
specific fields and functionality.

The IR classes form a hierarchy:
    - IRTemplate: Top-level container for the entire template
    - IRResource: A CloudFormation resource with properties
    - IRParameter: A template parameter
    - IROutput: A template output
    - IRMapping: A template mapping table (CloudFormation-specific)
    - IRCondition: A template condition expression (CloudFormation-specific)
    - IRProperty: A property key-value pair within a resource
    - IRIntrinsic: A parsed intrinsic function (CloudFormation-specific)

Example:
    >>> from wetwire_aws.importer.parser import parse_template
    >>> ir = parse_template("template.yaml")
    >>> for name, resource in ir.resources.items():
    ...     print(f"{name}: {resource.resource_type}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Import base classes from dataclass-dsl
from dataclass_dsl import (
    IROutput,
    IRParameter,
    IRProperty,
)


class IntrinsicType(Enum):
    """CloudFormation intrinsic function types.

    Each enum value corresponds to a CloudFormation intrinsic function.
    The string value is the canonical name used in CloudFormation JSON/YAML.

    See Also:
        AWS Intrinsic Function Reference:
        https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html
    """

    REF = "Ref"
    GET_ATT = "GetAtt"
    SUB = "Sub"
    JOIN = "Join"
    SELECT = "Select"
    GET_AZS = "GetAZs"
    IF = "If"
    EQUALS = "Equals"
    AND = "And"
    OR = "Or"
    NOT = "Not"
    CONDITION = "Condition"
    FIND_IN_MAP = "FindInMap"
    BASE64 = "Base64"
    CIDR = "Cidr"
    IMPORT_VALUE = "ImportValue"
    SPLIT = "Split"
    TRANSFORM = "Transform"
    VALUE_OF = "ValueOf"


@dataclass
class IRIntrinsic:
    """A parsed CloudFormation intrinsic function.

    Represents any CloudFormation intrinsic function (Ref, GetAtt, Sub, etc.)
    in a normalized form. The args structure varies by intrinsic type.

    Attributes:
        type: The intrinsic function type (IntrinsicType enum).
        args: Function arguments, structure depends on type:
            - Ref: str (logical_id)
            - GetAtt: tuple[str, str] (logical_id, attribute)
            - Sub: str or tuple[str, dict] (template, variables)
            - Join: tuple[str, list] (delimiter, values)
            - Select: tuple[int, Any] (index, list)
            - If: tuple[str, Any, Any] (condition_name, true_value, false_value)
            - Equals: tuple[Any, Any] (value1, value2)
            - And/Or: list[Any] (conditions)
            - Not: Any (condition)
            - FindInMap: tuple[str, Any, Any] (map_name, top_key, second_key)
            - Base64: Any (value to encode)
            - Cidr: tuple[Any, int, int] (ip_block, count, cidr_bits)
            - ImportValue: Any (export name)
            - Split: tuple[str, Any] (delimiter, source)
            - GetAZs: str (region, empty string for current)

    Example:
        >>> intrinsic = IRIntrinsic(IntrinsicType.REF, "MyBucket")
        >>> intrinsic.type
        <IntrinsicType.REF: 'Ref'>
    """

    type: IntrinsicType
    args: Any


# Re-export base IRProperty, IRParameter, IROutput from dataclass-dsl
# These are imported above and available directly
# IRProperty uses domain_name for the original property name (e.g., "BucketName")


@dataclass
class IRResource:
    """A parsed CloudFormation resource.

    Represents a resource from the Resources section of a CloudFormation
    template. Contains the resource type, all properties, and resource-level
    attributes like DependsOn and Condition.

    Extends the base dataclass-dsl IRResource with CloudFormation-specific
    fields like deletion_policy and update_replace_policy.

    Attributes:
        logical_id: The resource's logical name in the template.
        resource_type: CloudFormation resource type (e.g., "AWS::S3::Bucket").
        properties: Dictionary of property name to IRProperty.
        depends_on: List of logical IDs this resource depends on.
        condition: Name of condition that controls resource creation.
        deletion_policy: What happens when resource is deleted (Delete, Retain, Snapshot).
        update_replace_policy: What happens on replacement during update.
        metadata: Resource metadata (e.g., cfn-init configuration).

    Example:
        >>> resource = ir_template.resources["MyBucket"]
        >>> resource.resource_type
        'AWS::S3::Bucket'
        >>> resource.service
        'S3'
    """

    logical_id: str
    resource_type: str
    properties: dict[str, IRProperty] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    condition: str | None = None
    deletion_policy: str | None = None
    update_replace_policy: str | None = None
    metadata: dict[str, Any] | None = None

    @property
    def service(self) -> str:
        """Extract service name from the resource type.

        Returns:
            The AWS service name (e.g., "S3" from "AWS::S3::Bucket").
        """
        parts = self.resource_type.split("::")
        return parts[1] if len(parts) >= 2 else ""

    @property
    def type_name(self) -> str:
        """Extract the resource type name.

        Returns:
            The resource type (e.g., "Bucket" from "AWS::S3::Bucket").
        """
        parts = self.resource_type.split("::")
        return parts[2] if len(parts) >= 3 else ""


@dataclass
class IRMapping:
    """A parsed CloudFormation mapping.

    Represents a mapping from the Mappings section of a CloudFormation
    template. Mappings are two-level lookup tables used with Fn::FindInMap.

    Attributes:
        logical_id: The mapping's logical name in the template.
        map_data: Two-level dictionary of mapping values.
            Structure: {top_key: {second_key: value}}.

    Example:
        >>> mapping = ir_template.mappings["RegionAMI"]
        >>> mapping.map_data["us-east-1"]["HVM64"]
        'ami-0123456789abcdef0'

    See Also:
        AWS Mappings documentation:
        https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/mappings-section-structure.html
    """

    logical_id: str
    map_data: dict[str, dict[str, Any]]


@dataclass
class IRCondition:
    """A parsed CloudFormation condition.

    Represents a condition from the Conditions section of a CloudFormation
    template. Conditions control whether resources are created or properties
    are applied based on input parameters or other conditions.

    Attributes:
        logical_id: The condition's logical name in the template.
        expression: Condition expression as an IRIntrinsic. Typically uses
            Fn::Equals, Fn::And, Fn::Or, Fn::Not, or Fn::Condition.

    Example:
        >>> condition = ir_template.conditions["CreateProdResources"]
        >>> condition.expression.type
        <IntrinsicType.EQUALS: 'Equals'>

    See Also:
        AWS Conditions documentation:
        https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/conditions-section-structure.html
    """

    logical_id: str
    expression: Any


@dataclass
class IRTemplate:
    """Complete parsed CloudFormation template.

    The top-level IR structure containing all parsed sections of a
    CloudFormation template. This is the main output of the parser
    and the primary input to code generation.

    Attributes:
        description: Template description from the Description field.
        aws_template_format_version: Template format version (default: "2010-09-09").
        parameters: Dictionary of parameter name to IRParameter.
        mappings: Dictionary of mapping name to IRMapping.
        conditions: Dictionary of condition name to IRCondition.
        resources: Dictionary of resource logical ID to IRResource.
        outputs: Dictionary of output name to IROutput.
        source_file: Path to the source template file (for error messages).
        reference_graph: Dependency graph of resource references. Maps logical
            ID to list of logical IDs it references. Populated during parsing.

    Example:
        >>> from wetwire_aws.importer.parser import parse_template
        >>> ir = parse_template("template.yaml")
        >>> len(ir.resources)
        5
        >>> ir.description
        'My CloudFormation Stack'
    """

    description: str | None = None
    aws_template_format_version: str = "2010-09-09"

    parameters: dict[str, IRParameter] = field(default_factory=dict)
    mappings: dict[str, IRMapping] = field(default_factory=dict)
    conditions: dict[str, IRCondition] = field(default_factory=dict)
    resources: dict[str, IRResource] = field(default_factory=dict)
    outputs: dict[str, IROutput] = field(default_factory=dict)

    source_file: str | None = None
    reference_graph: dict[str, list[str]] = field(default_factory=dict)
