"""
CloudFormation intrinsic functions.

These classes represent intrinsic functions that are serialized to their
CloudFormation JSON equivalents during template generation.
"""

from dataclasses import dataclass
from typing import Any


class IntrinsicFunction:
    """Base class for all CloudFormation intrinsic functions.

    Subclasses implement to_dict() to produce their CloudFormation JSON representation.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert to CloudFormation-compatible dict.

        Returns:
            Dict representing the intrinsic function in CloudFormation format.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError


@dataclass
class Ref(IntrinsicFunction):
    """
    Reference to a resource or parameter.

    Args:
        logical_name: The logical name of the resource or parameter to reference.

    Example:
        >>> Ref("MyBucket").to_dict()
        {"Ref": "MyBucket"}
    """

    logical_name: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to CloudFormation Ref intrinsic.

        Returns:
            Dict with {"Ref": logical_name} structure.
        """
        return {"Ref": self.logical_name}


@dataclass
class GetAtt(IntrinsicFunction):
    """
    Get an attribute from a resource.

    Args:
        logical_name: The logical name of the resource.
        attribute_name: The name of the attribute to retrieve.

    Example:
        >>> GetAtt("MyBucket", "Arn").to_dict()
        {"Fn::GetAtt": ["MyBucket", "Arn"]}
    """

    logical_name: str
    attribute_name: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to CloudFormation Fn::GetAtt intrinsic.

        Returns:
            Dict with {"Fn::GetAtt": [logical_name, attribute_name]} structure.
        """
        return {"Fn::GetAtt": [self.logical_name, self.attribute_name]}


@dataclass
class Sub(IntrinsicFunction):
    """
    Substitute variables in a string.

    Args:
        template: Template string with ${VarName} placeholders.
        variables: Optional dict mapping variable names to values.
            If not provided, variables are resolved from resource/parameter names.

    Example:
        >>> Sub("arn:aws:s3:::${BucketName}/*").to_dict()
        {"Fn::Sub": "arn:aws:s3:::${BucketName}/*"}
        >>> Sub("Hello ${Name}", {"Name": Ref("NameParam")}).to_dict()
        {"Fn::Sub": ["Hello ${Name}", {"Name": {"Ref": "NameParam"}}]}
    """

    template: str
    variables: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.variables:
            resolved_vars = {
                k: v.to_dict() if isinstance(v, IntrinsicFunction) else v
                for k, v in self.variables.items()
            }
            return {"Fn::Sub": [self.template, resolved_vars]}
        return {"Fn::Sub": self.template}


@dataclass
class Join(IntrinsicFunction):
    """
    Join a list of values with a delimiter.

    Args:
        delimiter: The delimiter to join values with.
        values: List of values to join. Can include intrinsic functions.

    Example:
        >>> Join(",", ["a", "b", "c"]).to_dict()
        {"Fn::Join": [",", ["a", "b", "c"]]}
    """

    delimiter: str
    values: list[Any]

    def to_dict(self) -> dict[str, Any]:
        resolved = [
            v.to_dict() if isinstance(v, IntrinsicFunction) else v for v in self.values
        ]
        return {"Fn::Join": [self.delimiter, resolved]}


@dataclass
class Select(IntrinsicFunction):
    """
    Select an item from a list by index.

    Args:
        index: Zero-based index of the item to select.
        values: List or intrinsic function returning a list.

    Example:
        >>> Select(0, GetAZs("us-east-1")).to_dict()
        {"Fn::Select": ["0", {"Fn::GetAZs": "us-east-1"}]}
    """

    index: int
    values: Any

    def to_dict(self) -> dict[str, Any]:
        resolved = (
            self.values.to_dict()
            if isinstance(self.values, IntrinsicFunction)
            else self.values
        )
        return {"Fn::Select": [str(self.index), resolved]}


@dataclass
class If(IntrinsicFunction):
    """
    Conditional value based on a condition.

    Args:
        condition_name: Name of a condition defined in the template.
        value_if_true: Value to use if the condition is true.
        value_if_false: Value to use if the condition is false.

    Example:
        >>> If("CreateProdResources", "m5.xlarge", "t3.micro").to_dict()
        {"Fn::If": ["CreateProdResources", "m5.xlarge", "t3.micro"]}
    """

    condition_name: str
    value_if_true: Any
    value_if_false: Any

    def to_dict(self) -> dict[str, Any]:
        true_val = (
            self.value_if_true.to_dict()
            if isinstance(self.value_if_true, IntrinsicFunction)
            else self.value_if_true
        )
        false_val = (
            self.value_if_false.to_dict()
            if isinstance(self.value_if_false, IntrinsicFunction)
            else self.value_if_false
        )
        return {"Fn::If": [self.condition_name, true_val, false_val]}


@dataclass
class Equals(IntrinsicFunction):
    """
    Compare two values for equality.

    Args:
        value1: First value to compare.
        value2: Second value to compare.

    Example:
        >>> Equals(Ref("Environment"), "prod").to_dict()
        {"Fn::Equals": [{"Ref": "Environment"}, "prod"]}
    """

    value1: Any
    value2: Any

    def to_dict(self) -> dict[str, Any]:
        v1 = (
            self.value1.to_dict()
            if isinstance(self.value1, IntrinsicFunction)
            else self.value1
        )
        v2 = (
            self.value2.to_dict()
            if isinstance(self.value2, IntrinsicFunction)
            else self.value2
        )
        return {"Fn::Equals": [v1, v2]}


@dataclass
class And(IntrinsicFunction):
    """
    Logical AND of conditions.

    Args:
        conditions: List of conditions to AND together. Must have 2-10 conditions.

    Example:
        >>> And([Condition("IsProd"), Condition("IsUsEast1")]).to_dict()
        {"Fn::And": [{"Condition": "IsProd"}, {"Condition": "IsUsEast1"}]}
    """

    conditions: list[Any]

    def to_dict(self) -> dict[str, Any]:
        resolved = [
            c.to_dict() if isinstance(c, IntrinsicFunction) else c
            for c in self.conditions
        ]
        return {"Fn::And": resolved}


@dataclass
class Or(IntrinsicFunction):
    """
    Logical OR of conditions.

    Args:
        conditions: List of conditions to OR together. Must have 2-10 conditions.

    Example:
        >>> Or([Condition("IsProd"), Condition("IsStaging")]).to_dict()
        {"Fn::Or": [{"Condition": "IsProd"}, {"Condition": "IsStaging"}]}
    """

    conditions: list[Any]

    def to_dict(self) -> dict[str, Any]:
        resolved = [
            c.to_dict() if isinstance(c, IntrinsicFunction) else c
            for c in self.conditions
        ]
        return {"Fn::Or": resolved}


@dataclass
class Not(IntrinsicFunction):
    """
    Logical NOT of a condition.

    Args:
        condition: The condition to negate.

    Example:
        >>> Not(Condition("IsProd")).to_dict()
        {"Fn::Not": [{"Condition": "IsProd"}]}
    """

    condition: Any

    def to_dict(self) -> dict[str, Any]:
        resolved = (
            self.condition.to_dict()
            if isinstance(self.condition, IntrinsicFunction)
            else self.condition
        )
        return {"Fn::Not": [resolved]}


@dataclass
class Base64(IntrinsicFunction):
    """
    Base64 encode a string.

    Args:
        value: String or intrinsic function to encode.

    Example:
        >>> Base64("#!/bin/bash\\necho hello").to_dict()
        {"Fn::Base64": "#!/bin/bash\\necho hello"}
    """

    value: Any

    def to_dict(self) -> dict[str, Any]:
        resolved = (
            self.value.to_dict()
            if isinstance(self.value, IntrinsicFunction)
            else self.value
        )
        return {"Fn::Base64": resolved}


@dataclass
class GetAZs(IntrinsicFunction):
    """
    Get the list of availability zones for a region.

    Args:
        region: AWS region name. Empty string uses the current region.

    Example:
        >>> GetAZs("us-east-1").to_dict()
        {"Fn::GetAZs": "us-east-1"}
    """

    region: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to CloudFormation Fn::GetAZs intrinsic.

        Returns:
            Dict with {"Fn::GetAZs": region} structure.
        """
        return {"Fn::GetAZs": self.region}


@dataclass
class ImportValue(IntrinsicFunction):
    """
    Import a value exported from another stack.

    Args:
        export_name: The name of the cross-stack export, or an intrinsic function.

    Example:
        >>> ImportValue("NetworkStack-VpcId").to_dict()
        {"Fn::ImportValue": "NetworkStack-VpcId"}
    """

    export_name: Any

    def to_dict(self) -> dict[str, Any]:
        resolved = (
            self.export_name.to_dict()
            if isinstance(self.export_name, IntrinsicFunction)
            else self.export_name
        )
        return {"Fn::ImportValue": resolved}


@dataclass
class Condition(IntrinsicFunction):
    """
    Reference to a condition defined in the template.

    Args:
        condition_name: The name of the condition.

    Example:
        >>> Condition("IsProd").to_dict()
        {"Condition": "IsProd"}
    """

    condition_name: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to CloudFormation Condition reference.

        Returns:
            Dict with {"Condition": condition_name} structure.
        """
        return {"Condition": self.condition_name}


@dataclass
class FindInMap(IntrinsicFunction):
    """
    Find a value in a mapping.

    Args:
        map_name: Name of the mapping defined in the template.
        top_level_key: First-level key in the mapping.
        second_level_key: Second-level key in the mapping.

    Example:
        >>> FindInMap("RegionMap", Ref("AWS::Region"), "AMI").to_dict()
        {"Fn::FindInMap": ["RegionMap", {"Ref": "AWS::Region"}, "AMI"]}
    """

    map_name: str
    top_level_key: Any
    second_level_key: Any

    def to_dict(self) -> dict[str, Any]:
        top = (
            self.top_level_key.to_dict()
            if isinstance(self.top_level_key, IntrinsicFunction)
            else self.top_level_key
        )
        second = (
            self.second_level_key.to_dict()
            if isinstance(self.second_level_key, IntrinsicFunction)
            else self.second_level_key
        )
        return {"Fn::FindInMap": [self.map_name, top, second]}


@dataclass
class Split(IntrinsicFunction):
    """
    Split a string by a delimiter.

    Args:
        delimiter: The delimiter to split on.
        source: String or intrinsic function to split.

    Example:
        >>> Split(",", "a,b,c").to_dict()
        {"Fn::Split": [",", "a,b,c"]}
    """

    delimiter: str
    source: Any

    def to_dict(self) -> dict[str, Any]:
        resolved = (
            self.source.to_dict()
            if isinstance(self.source, IntrinsicFunction)
            else self.source
        )
        return {"Fn::Split": [self.delimiter, resolved]}


@dataclass
class Transform(IntrinsicFunction):
    """
    Apply a transform macro.

    Args:
        name: Name of the macro (e.g., "AWS::Include", "AWS::Serverless-2016-10-31").
        parameters: Parameters to pass to the macro.

    Example:
        >>> Transform("AWS::Include", {"Location": "s3://bucket/template.yaml"}).to_dict()
        {"Fn::Transform": {"Name": "AWS::Include", "Parameters": {"Location": "..."}}}
    """

    name: str
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        resolved_params = {
            k: v.to_dict() if isinstance(v, IntrinsicFunction) else v
            for k, v in self.parameters.items()
        }
        return {"Fn::Transform": {"Name": self.name, "Parameters": resolved_params}}


@dataclass
class Cidr(IntrinsicFunction):
    """
    Generate CIDR blocks.

    Args:
        ip_block: The CIDR block to subnet, or intrinsic function returning one.
        count: Number of CIDR blocks to generate (1-256).
        cidr_bits: Number of subnet bits for the CIDR (determines subnet size).

    Example:
        >>> Cidr(GetAtt("Vpc", "CidrBlock"), 6, 8).to_dict()
        {"Fn::Cidr": [{"Fn::GetAtt": ["Vpc", "CidrBlock"]}, 6, 8]}
    """

    ip_block: Any
    count: int
    cidr_bits: int

    def to_dict(self) -> dict[str, Any]:
        resolved = (
            self.ip_block.to_dict()
            if isinstance(self.ip_block, IntrinsicFunction)
            else self.ip_block
        )
        return {"Fn::Cidr": [resolved, self.count, self.cidr_bits]}
