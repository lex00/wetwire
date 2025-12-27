"""
CloudFormation template generation.

CloudFormationTemplate collects registered resources and generates
valid CloudFormation JSON or YAML.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from wetwire_aws.decorator import get_aws_registry
from wetwire_aws.intrinsics.functions import IntrinsicFunction


@dataclass
class Parameter:
    """CloudFormation template parameter."""

    type: str
    description: str = ""
    default: Any = None
    allowed_values: list[str] | None = None
    allowed_pattern: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    min_value: int | None = None
    max_value: int | None = None
    no_echo: bool = False
    constraint_description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"Type": self.type}
        if self.description:
            result["Description"] = self.description
        if self.default is not None:
            result["Default"] = self.default
        if self.allowed_values:
            result["AllowedValues"] = self.allowed_values
        if self.allowed_pattern:
            result["AllowedPattern"] = self.allowed_pattern
        if self.min_length is not None:
            result["MinLength"] = self.min_length
        if self.max_length is not None:
            result["MaxLength"] = self.max_length
        if self.min_value is not None:
            result["MinValue"] = self.min_value
        if self.max_value is not None:
            result["MaxValue"] = self.max_value
        if self.no_echo:
            result["NoEcho"] = True
        if self.constraint_description:
            result["ConstraintDescription"] = self.constraint_description
        return result


@dataclass
class Output:
    """CloudFormation template output."""

    value: Any
    description: str = ""
    export_name: str | None = None
    condition: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = (
            self.value.to_dict()
            if isinstance(self.value, IntrinsicFunction)
            else self.value
        )
        result: dict[str, Any] = {"Value": value}
        if self.description:
            result["Description"] = self.description
        if self.export_name:
            result["Export"] = {"Name": self.export_name}
        if self.condition:
            result["Condition"] = self.condition
        return result


@dataclass
class CloudFormationTemplate:
    """
    CloudFormation template container.

    Collects resources, parameters, outputs, and generates
    valid CloudFormation JSON or YAML.
    """

    description: str = ""
    parameters: dict[str, Parameter] = field(default_factory=dict)
    mappings: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    conditions: dict[str, Any] = field(default_factory=dict)
    resources: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Output] = field(default_factory=dict)
    transform: str | list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_registry(
        cls,
        scope_package: str | None = None,
        description: str = "",
        parameters: dict[str, Parameter] | None = None,
        outputs: dict[str, Output] | None = None,
    ) -> "CloudFormationTemplate":
        """
        Create a template from registered resources.

        Resources are topologically sorted by dependencies using graph-refs
        get_dependencies(), so resources appear in creation order.

        Args:
            scope_package: Optional package name to filter resources
            description: Template description
            parameters: Template parameters
            outputs: Template outputs

        Returns:
            CloudFormationTemplate with all registered resources
        """
        registry = get_aws_registry()
        resources: dict[str, Any] = {}

        from typing import get_type_hints

        from wetwire import is_attr_ref, is_class_ref, topological_sort

        from wetwire_aws.intrinsics.functions import GetAtt
        from wetwire_aws.intrinsics.functions import Ref as RefIntrinsic
        from wetwire_aws.intrinsics.refs import resolve_refs_from_annotations

        # Get all wrapper classes
        all_wrappers = list(registry.get_all(scope_package))

        # Topologically sort by dependencies (uses graph-refs internally)
        sorted_wrappers = topological_sort(all_wrappers)

        for wrapper_cls in sorted_wrappers:
            logical_name = wrapper_cls.__name__

            # Get resource type from 'resource' annotation (resolve forward refs)
            try:
                hints = get_type_hints(wrapper_cls)
                resource_type_cls = hints.get("resource")
            except Exception:
                # Fallback to raw annotations if get_type_hints fails
                annotations = getattr(wrapper_cls, "__annotations__", {})
                resource_type_cls = annotations.get("resource")

            if resource_type_cls is None or not hasattr(
                resource_type_cls, "_resource_type"
            ):
                continue

            # Create wrapper instance to get property values
            wrapper_instance = wrapper_cls()

            # Resolve Ref[T] and Attr[T, "name"] annotations to intrinsics
            resolved_refs = resolve_refs_from_annotations(wrapper_instance)

            # Collect properties from wrapper (excluding 'resource' and private attrs)
            # Also exclude fields that are None (annotation-only placeholders)
            props: dict[str, Any] = {}
            for k, v in wrapper_instance.__dict__.items():
                if k.startswith("_") or k == "resource" or v is None:
                    continue

                # Handle no-parens pattern: AttrRef markers (e.g., MyRole.Arn)
                if is_attr_ref(v):
                    props[k] = GetAtt(v.target.__name__, v.attr)
                # Handle no-parens pattern: class references (e.g., MyVPC)
                elif is_class_ref(v):
                    props[k] = RefIntrinsic(v.__name__)
                elif isinstance(v, type) and hasattr(v, "_wetwire_marker"):
                    props[k] = RefIntrinsic(v.__name__)
                else:
                    props[k] = v

            # Merge resolved refs - these are the graph-refs annotations resolved
            # to CloudFormation intrinsics. Only include refs that resolve to
            # fields the resource actually accepts.
            for field_name, ref_value in resolved_refs.items():
                # Don't overwrite already-resolved no-parens refs
                if field_name not in props:
                    props[field_name] = ref_value

            # Create resource instance with collected properties
            resource_instance = resource_type_cls(**props)
            resources[logical_name] = resource_instance.to_dict()

        return cls(
            description=description,
            parameters=parameters or {},
            resources=resources,
            outputs=outputs or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert template to CloudFormation-compatible dict."""
        result: dict[str, Any] = {
            "AWSTemplateFormatVersion": "2010-09-09",
        }

        if self.description:
            result["Description"] = self.description

        if self.transform:
            result["Transform"] = self.transform

        if self.metadata:
            result["Metadata"] = self.metadata

        if self.parameters:
            result["Parameters"] = {
                name: param.to_dict() for name, param in self.parameters.items()
            }

        if self.mappings:
            result["Mappings"] = self.mappings

        if self.conditions:
            result["Conditions"] = self._resolve_conditions(self.conditions)

        # Resources is always included (empty dict if none)
        result["Resources"] = (
            self._resolve_resources(self.resources) if self.resources else {}
        )

        if self.outputs:
            result["Outputs"] = {
                name: output.to_dict() for name, output in self.outputs.items()
            }

        return result

    def _resolve_resources(self, resources: dict[str, Any]) -> dict[str, Any]:
        """Resolve any intrinsic functions in resources."""
        resolved: dict[str, Any] = self._resolve_value(resources)
        return resolved

    def _resolve_conditions(self, conditions: dict[str, Any]) -> dict[str, Any]:
        """Resolve any intrinsic functions in conditions."""
        return {
            name: (cond.to_dict() if isinstance(cond, IntrinsicFunction) else cond)
            for name, cond in conditions.items()
        }

    def _resolve_value(self, value: Any) -> Any:
        """Recursively resolve intrinsic functions in a value."""
        if isinstance(value, IntrinsicFunction):
            return value.to_dict()
        elif isinstance(value, dict):
            return {k: self._resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_value(v) for v in value]
        else:
            return value

    def to_json(self, indent: int = 2) -> str:
        """Generate CloudFormation JSON."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_yaml(self) -> str:
        """Generate CloudFormation YAML."""
        try:
            import yaml

            return yaml.dump(
                self.to_dict(),
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        except ImportError:
            raise ImportError("PyYAML is required for YAML output: pip install pyyaml")

    def add_parameter(
        self,
        name: str,
        *,
        type: str,
        description: str = "",
        default: Any = None,
        allowed_values: list[str] | None = None,
        allowed_pattern: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        no_echo: bool = False,
        constraint_description: str | None = None,
    ) -> None:
        """Add a parameter to the template."""
        self.parameters[name] = Parameter(
            type=type,
            description=description,
            default=default,
            allowed_values=allowed_values,
            allowed_pattern=allowed_pattern,
            min_length=min_length,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
            no_echo=no_echo,
            constraint_description=constraint_description,
        )

    def add_output(
        self,
        name: str,
        *,
        value: Any,
        description: str = "",
        export_name: str | None = None,
        condition: str | None = None,
    ) -> None:
        """Add an output to the template."""
        self.outputs[name] = Output(
            value=value,
            description=description,
            export_name=export_name,
            condition=condition,
        )

    def add_resource(self, logical_name: str, resource: Any) -> None:
        """Add a resource to the template."""
        if hasattr(resource, "to_dict"):
            self.resources[logical_name] = resource.to_dict()
        else:
            self.resources[logical_name] = resource

    def add_condition(self, name: str, condition: Any) -> None:
        """Add a condition to the template."""
        self.conditions[name] = condition

    def add_mapping(self, name: str, mapping: dict[str, dict[str, Any]]) -> None:
        """Add a mapping to the template."""
        self.mappings[name] = mapping
