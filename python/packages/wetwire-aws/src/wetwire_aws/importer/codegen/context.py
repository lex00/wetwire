"""Code generation context classes.

This module provides context objects that track state during Python code
generation from CloudFormation IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from wetwire_aws.importer.ir import IRTemplate


@dataclass
class AnnotatedValue:
    """A field value that requires an explicit type annotation.

    Used when generating annotation-based references instead of string-based.
    For example, generates: bucket: Ref[Bucket] = ref()
    Instead of: bucket = ref("Bucket")

    Attributes:
        annotation: The type annotation string (e.g., "Ref[Bucket]").
        value: The value expression (e.g., "ref()").
    """

    annotation: str
    value: str


@dataclass
class CodegenContext:
    """Context for tracking state during code generation.

    Maintains imports, generated class names, and analysis data used by
    the code generator.

    Attributes:
        template: The parsed IR template being converted.
        include_docstrings: Whether to include docstrings in output.
        include_main_block: Whether to include if __name__ == "__main__" block.
        generated_classes: Set of class names already generated.
        imports: Map of module name to set of names to import from it.
        intrinsic_imports: Set of intrinsic function names to import.
        current_module: AWS module being processed.
        current_resource_id: Resource currently being generated (avoid self-refs).
        forward_references: Resource IDs that need string-based refs.
        name_pattern_map: Map Sub patterns to resource IDs for ref() detection.
        arn_pattern_map: Map ARN patterns to (resource_id, suffix) for get_att().
    """

    template: IRTemplate
    include_docstrings: bool = True
    include_main_block: bool = True

    generated_classes: set[str] = field(default_factory=set)
    imports: dict[str, set[str]] = field(default_factory=dict)
    intrinsic_imports: set[str] = field(default_factory=set)

    current_module: str | None = None
    current_resource_id: str | None = None
    current_resource_file: str | None = None  # File where current resource is generated
    forward_references: set[str] = field(default_factory=set)

    # When True, all resource refs use forward reference (string) syntax.
    # Used when generating PropertyType wrappers that appear before resource classes.
    in_property_type_wrapper: bool = False

    # Maps resource ID to the file it will be generated in (e.g., "compute", "network", "main")
    # Used to determine if cross-file references need forward ref syntax
    resource_to_file: dict[str, str] = field(default_factory=dict)

    name_pattern_map: dict[str, str] = field(default_factory=dict)
    arn_pattern_map: dict[str, tuple[str, str]] = field(default_factory=dict)

    # PropertyType flattening: generated wrapper class definitions (in order)
    property_type_class_defs: list[str] = field(default_factory=list)

    # Policy flattening: generated PolicyDocument/PolicyStatement classes
    # Maps class name -> class definition string
    policy_classes: dict[str, str] = field(default_factory=dict)
    # Counter for generating unique statement class names
    _policy_counter: int = field(default=0)

    def add_import(self, module: str, name: str) -> None:
        """Register an import to include in generated code.

        Args:
            module: The module path (e.g., "wetwire_aws.resources.s3").
            name: The name to import from the module.
        """
        self.imports.setdefault(module, set()).add(name)

    def add_intrinsic_import(self, name: str) -> None:
        """Register an intrinsic function import.

        Args:
            name: The intrinsic function name (e.g., "Sub", "Join").
        """
        self.intrinsic_imports.add(name)

    def next_policy_counter(self) -> int:
        """Get the next unique counter for policy class naming."""
        counter = self._policy_counter
        self._policy_counter += 1
        return counter

    def add_policy_class(self, class_name: str, class_def: str) -> None:
        """Register a generated policy class.

        Args:
            class_name: The class name (e.g., "MyRoleAllowStatement0").
            class_def: The complete class definition string.
        """
        self.policy_classes[class_name] = class_def


@dataclass
class PackageContext:
    """Context for multi-file package generation.

    Extends CodegenContext to track per-file imports and exports when
    generating a complete Python package.

    Attributes:
        template: The parsed IR template being converted.
        init_imports: Per-file import tracking for __init__.py.
        config_exports: Classes exported from config module.
        resources_exports: Classes exported from resources module.
        outputs_exports: Classes exported from outputs module.
        codegen_ctx: Underlying CodegenContext for class generation.
    """

    template: IRTemplate

    init_imports: dict[str, set[str]] = field(default_factory=dict)
    config_exports: set[str] = field(default_factory=set)
    resources_exports: set[str] = field(default_factory=set)
    outputs_exports: set[str] = field(default_factory=set)

    codegen_ctx: CodegenContext = field(default=None)  # type: ignore

    def __post_init__(self) -> None:
        """Initialize CodegenContext if not provided."""
        if self.codegen_ctx is None:
            self.codegen_ctx = CodegenContext(template=self.template)
            self.codegen_ctx.name_pattern_map = build_name_pattern_map(self.template)
            self.codegen_ctx.arn_pattern_map = build_arn_pattern_map(self.template)


# =============================================================================
# Pattern Map Building (for implicit ref/get_att detection)
# =============================================================================


# Properties that define a resource's "name" for implicit ref detection
NAME_PROPERTIES = frozenset(
    [
        "BucketName",  # S3
        "RoleName",  # IAM
        "TableName",  # DynamoDB
        "FunctionName",  # Lambda
        "QueueName",  # SQS
        "TopicName",  # SNS
        "StackName",  # CloudFormation
        "ClusterName",  # ECS, EKS, etc.
        "LogGroupName",  # CloudWatch Logs
        "StreamName",  # Kinesis
        "DatabaseName",  # RDS, Glue
        "RepositoryName",  # ECR
        "VaultName",  # Glacier
        "DomainName",  # Various services
        "Name",  # Generic fallback
    ]
)


def build_name_pattern_map(template: IRTemplate) -> dict[str, str]:
    """Build a map of Sub template patterns to resource logical IDs.

    This enables detecting when a Sub pattern matches a resource's name,
    allowing replacement with ref() for proper dependency tracking.

    NOTE: Patterns that only contain pseudo-parameters (like ${AWS::StackName})
    are excluded since multiple resources may use the same pattern without
    referencing each other.
    """
    import re

    from wetwire_aws.importer.ir import IntrinsicType, IRIntrinsic

    pattern_map: dict[str, str] = {}

    for logical_id, resource in template.resources.items():
        for prop_cf_name in NAME_PROPERTIES:
            if prop_cf_name in resource.properties:
                prop = resource.properties[prop_cf_name]
                # Check if it's a Sub intrinsic
                if (
                    isinstance(prop.value, IRIntrinsic)
                    and prop.value.type == IntrinsicType.SUB
                ):
                    # Extract the template string
                    if isinstance(prop.value.args, str):
                        template_str = prop.value.args
                    elif (
                        isinstance(prop.value.args, (list, tuple))
                        and len(prop.value.args) >= 1
                    ):
                        template_str = prop.value.args[0]
                    else:
                        continue

                    # Skip patterns that only contain pseudo-parameters
                    # These are not resource references but stack-level values
                    var_refs = re.findall(r"\$\{([^}]+)\}", template_str)
                    non_pseudo_vars = [v for v in var_refs if not v.startswith("AWS::")]
                    # Only include patterns that reference actual resource names
                    # or parameter values (non-pseudo-parameter variables)
                    if not non_pseudo_vars:
                        # Pattern only contains pseudo-parameters, skip it
                        continue

                    # Store the mapping (first occurrence wins)
                    if template_str not in pattern_map:
                        pattern_map[template_str] = logical_id

    return pattern_map


# ARN prefix patterns by CloudFormation resource type
ARN_PREFIX_PATTERNS: dict[str, str] = {
    "AWS::S3::Bucket": "arn:${AWS::Partition}:s3:::",
    "AWS::IAM::Role": "arn:${AWS::Partition}:iam::${AWS::AccountId}:role/",
    "AWS::IAM::Policy": "arn:${AWS::Partition}:iam::${AWS::AccountId}:policy/",
    "AWS::Lambda::Function": "arn:${AWS::Partition}:lambda:${AWS::Region}:${AWS::AccountId}:function:",
    "AWS::DynamoDB::Table": "arn:${AWS::Partition}:dynamodb:${AWS::Region}:${AWS::AccountId}:table/",
    "AWS::SQS::Queue": "arn:${AWS::Partition}:sqs:${AWS::Region}:${AWS::AccountId}:",
    "AWS::SNS::Topic": "arn:${AWS::Partition}:sns:${AWS::Region}:${AWS::AccountId}:",
    "AWS::Logs::LogGroup": "arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:",
}


def build_arn_pattern_map(template: IRTemplate) -> dict[str, tuple[str, str]]:
    """Build a map of ARN Sub patterns to (resource_id, suffix).

    This enables detecting when a Sub pattern builds an ARN that matches
    a resource's name pattern, allowing replacement with get_att(Resource, "Arn").
    """
    from wetwire_aws.importer.ir import IntrinsicType, IRIntrinsic

    arn_map: dict[str, tuple[str, str]] = {}

    for logical_id, resource in template.resources.items():
        # Get the ARN prefix for this resource type
        arn_prefix = ARN_PREFIX_PATTERNS.get(resource.resource_type)
        if not arn_prefix:
            continue

        # Find the resource's name pattern
        for prop_cf_name in NAME_PROPERTIES:
            if prop_cf_name in resource.properties:
                prop = resource.properties[prop_cf_name]
                if (
                    isinstance(prop.value, IRIntrinsic)
                    and prop.value.type == IntrinsicType.SUB
                ):
                    if isinstance(prop.value.args, str):
                        name_pattern = prop.value.args
                    elif (
                        isinstance(prop.value.args, (list, tuple))
                        and len(prop.value.args) >= 1
                    ):
                        name_pattern = prop.value.args[0]
                    else:
                        continue

                    # Build the full ARN pattern
                    full_arn = f"{arn_prefix}{name_pattern}"

                    # Store exact match
                    if full_arn not in arn_map:
                        arn_map[full_arn] = (logical_id, "")

                    # Also store wildcard variant
                    wildcard_arn = f"{full_arn}/*"
                    if wildcard_arn not in arn_map:
                        arn_map[wildcard_arn] = (logical_id, "/*")

    return arn_map
