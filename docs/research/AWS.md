# Wetwire AWS Feasibility Study

**Status**: Proven (reference implementation)
**Purpose**: Document the design decisions and architecture of `wetwire-aws` as a reference for other implementations.
**Scope**: **Synthesis only** - generates CloudFormation JSON; does not perform diff/deploy.
**Recommendation**: **Proven viable** - CloudFormation JSON as output, CF Spec + botocore as schema sources.

---

## Executive Summary

`wetwire-aws` is a **synthesis library** - it generates CloudFormation JSON from decorated classes. It does not perform deployment operations.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  wetwire-aws (synthesis)              External tools (deployment)       │
│                                                                          │
│  CF Spec + botocore → Typed Classes → CloudFormation JSON               │
│      (schema)           (authoring)       (output)                       │
│                                               ↓                          │
│                                      aws cloudformation deploy          │
│                                      (user's responsibility)             │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why CloudFormation JSON as output:**
- Native AWS tooling (`aws` CLI is ubiquitous)
- **Native Change Sets** - diff/preview before deployment
- No external toolchain dependency
- AWS's native IaC format (CDK, SAM compile to it)

---

## Vision

**wetwire-aws is a synthesis library.** It generates CloudFormation JSON from typed classes. It does not deploy, diff, or manage state - those are the user's responsibility via AWS CLI.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        wetwire-aws (this project)                        │
│                                                                          │
│   class MyBucket:                       Template.from_registry()         │
│       resource: s3.Bucket                      ↓                         │
│       bucket_name = "my-bucket"         print(template.to_json())        │
│       versioning = ref(VersioningConfig)       ↓                         │
│                                         CloudFormation JSON              │
├─────────────────────────────────────────────────────────────────────────┤
│                    User's toolchain (external)                           │
│                                                                          │
│   aws cloudformation deploy             # Deploy (creates change set)    │
│   aws cloudformation describe-stacks    # View stack                     │
│   aws cloudformation delete-stack       # Delete                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Parallel to other domains:**

| Aspect | wetwire-aws | wetwire-gcp | wetwire-azure |
|--------|-------------|-------------|---------------|
| **Scope** | Synthesis only | Synthesis only | Synthesis only |
| **Output** | CloudFormation JSON | Config Connector YAML | ARM JSON |
| **Deploy tool** | `aws cloudformation` | `kubectl apply` | `az deployment` |
| **Diff tool** | Change Sets (native) | `kubectl diff` | `what-if` (native) |

**Core principles:**
1. **Synthesis only** - Generate JSON, don't deploy it
2. **CF Spec + botocore as source** - AWS's schema for all resources
3. **Declarative wrapper pattern** - `@wetwire` decorator with `resource:` field
4. **Native experience** - `ref()`, `get_att()`, type-safe IDE autocomplete

---

## Why CloudFormation JSON?

### The AWS IaC Landscape

| Tool | Status | Native AWS | Diff Capability |
|------|--------|------------|-----------------|
| **CloudFormation** | Foundation | Yes | Change Sets (native) |
| **CDK** | **Recommended** | Yes (compiles to CF) | Change Sets (native) |
| **SAM** | Active | Serverless (compiles to CF) | Change Sets (native) |
| **Terraform** | Popular | No | `terraform plan` |

### Why CloudFormation Wins

**1. Native Change Sets (diff/preview)**

```bash
# Create change set for review
aws cloudformation create-change-set \
  --template-body file://template.json \
  --stack-name my-stack \
  --change-set-name my-changes

# Review changes
aws cloudformation describe-change-set \
  --stack-name my-stack \
  --change-set-name my-changes
```

This is a **native AWS feature** - no external toolchain required.

**2. No external dependencies**

| Output Format | External Tool | Native AWS |
|---------------|---------------|------------|
| **CloudFormation JSON** | `aws` CLI | Yes |
| Terraform HCL | `terraform` CLI | No |
| Pulumi | `pulumi` CLI | No |

**3. AWS's native format**

CDK, SAM, and other AWS tools compile to CloudFormation JSON. By outputting CF JSON, wetwire-aws integrates with the entire AWS ecosystem.

---

## Schema Source

### The Two-Source Challenge

CloudFormation Resource Specification provides:
- Resource types and property structures
- Required vs optional fields
- GetAtt return values

But CloudFormation spec does **NOT** provide:
- Enum values (e.g., `BillingMode = "PROVISIONED" | "PAY_PER_REQUEST"`)
- Valid string literals for constrained fields

### Solution: CF Spec + botocore

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Schema Sources                                        │
│                                                                          │
│   CloudFormation Spec (JSON)         botocore service models             │
│   - Resource types                   - Enum values                       │
│   - Property structures              - String literals                   │
│   - Required/optional fields         - API shapes                        │
│   - GetAtt attributes                                                    │
│           ↓                                   ↓                          │
│           └───────────── Combined ───────────┘                           │
│                              ↓                                           │
│                       wetwire-aws                                        │
│                    Typed classes + enums                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### Schema Locations

| Source | Location | Format |
|--------|----------|--------|
| CF Spec | AWS CDN (CloudFormationResourceSpecification.json) | JSON |
| botocore | pip install botocore | Package with service models |

### Comparison to Other Domains

| Aspect | wetwire-aws | wetwire-gcp | wetwire-azure |
|--------|-------------|-------------|---------------|
| Schema source | CF Spec + botocore | Config Connector CRDs | ARM schemas |
| Schema location | AWS CDN + pip | GitHub | GitHub |
| Enum source | botocore (separate) | CRD schemas | ARM schemas |
| Schema format | JSON + Python | YAML | JSON |
| Unified source | No (two sources) | Yes | Yes |

**Note:** wetwire-aws requires two sources (CF spec + botocore), while GCP and Azure have unified sources.

---

## The `ref()` Pattern

CloudFormation uses `Ref` and `Fn::GetAtt` intrinsic functions:

```json
{
  "Type": "AWS::Lambda::Function",
  "Properties": {
    "Role": { "Fn::GetAtt": ["MyRole", "Arn"] },
    "Environment": {
      "Variables": {
        "BUCKET": { "Ref": "MyBucket" }
      }
    }
  }
}
```

**This maps to wetwire-aws:**

```python
class MyBucket:
    resource: s3.Bucket
    bucket_name = "my-bucket"

class MyRole:
    resource: iam.Role
    assume_role_policy_document = ...

class MyFunction:
    resource: lambda_.Function
    role = get_att(MyRole, ARN)           # → {"Fn::GetAtt": ["MyRole", "Arn"]}
    environment = {"BUCKET": ref(MyBucket)}  # → {"Ref": "MyBucket"}
```

**Reference types:**
- `ref(Resource)` - Reference to resource logical ID (`{"Ref": "..."}`)
- `get_att(Resource, Attribute)` - Reference to resource attribute (`{"Fn::GetAtt": [...]}`)
- `Ref("ParameterName")` - Reference to template parameter

---

## Intrinsic Functions

CloudFormation provides intrinsic functions for runtime operations:

| Function | wetwire-aws | Output |
|----------|-------------|--------|
| `ref(MyBucket)` | Resource reference | `{"Ref": "MyBucket"}` |
| `get_att(MyBucket, ARN)` | Attribute reference | `{"Fn::GetAtt": ["MyBucket", "Arn"]}` |
| `Sub("${AWS::Region}-bucket")` | String substitution | `{"Fn::Sub": "..."}` |
| `Join(",", [...])` | Join list | `{"Fn::Join": [",", [...]]}` |
| `Select(0, list)` | Select from list | `{"Fn::Select": [0, ...]}` |
| `If(cond, a, b)` | Conditional | `{"Fn::If": [...]}` |
| `Equals(a, b)` | Equality check | `{"Fn::Equals": [...]}` |
| `And(a, b)` / `Or(a, b)` | Boolean logic | `{"Fn::And": [...]}` |
| `Base64(str)` | Base64 encode | `{"Fn::Base64": "..."}` |
| `GetAZs(region)` | Get availability zones | `{"Fn::GetAZs": "..."}` |

### Pseudo-Parameters

| wetwire-aws | CloudFormation | Description |
|-------------|----------------|-------------|
| `AWS_REGION` | `AWS::Region` | Current region |
| `AWS_ACCOUNT_ID` | `AWS::AccountId` | Account ID |
| `AWS_STACK_NAME` | `AWS::StackName` | Stack name |
| `AWS_STACK_ID` | `AWS::StackId` | Stack ID |
| `AWS_PARTITION` | `AWS::Partition` | Partition (aws, aws-cn, etc.) |

---

## Dependency Handling

CloudFormation automatically determines dependency order from `Ref` and `GetAtt` usage. Explicit `DependsOn` is rarely needed.

### How It Works

```python
class MyBucket:
    resource: s3.Bucket

class MyFunction:
    resource: lambda_.Function
    environment = {"BUCKET": ref(MyBucket)}  # Implicit dependency
```

**Generated JSON includes implicit dependency:**
```json
{
  "MyFunction": {
    "Type": "AWS::Lambda::Function",
    "Properties": {
      "Environment": {
        "Variables": {
          "BUCKET": {"Ref": "MyBucket"}
        }
      }
    }
  }
}
```

CloudFormation sees the `Ref` and creates MyBucket before MyFunction.

### Explicit Dependencies

For dependencies without intrinsic function references:

```python
class MyFunction:
    resource: lambda_.Function
    depends_on = [MyBucket]  # Explicit DependsOn
```

---

## User Workflow (External to wetwire-aws)

wetwire-aws generates JSON. The user handles diff and deploy with AWS CLI:

```bash
# 1. Generate CloudFormation JSON (wetwire-aws)
wetwire build > template.json

# 2. Deploy with change set (AWS CLI - external)
aws cloudformation deploy \
  --template-file template.json \
  --stack-name my-stack \
  --capabilities CAPABILITY_IAM

# 3. Or create change set manually for review
aws cloudformation create-change-set \
  --template-body file://template.json \
  --stack-name my-stack \
  --change-set-name my-changes

# 4. Review changes
aws cloudformation describe-change-set \
  --stack-name my-stack \
  --change-set-name my-changes

# 5. Execute change set
aws cloudformation execute-change-set \
  --stack-name my-stack \
  --change-set-name my-changes
```

### Change Sets: Native Diff

CloudFormation Change Sets provide **native diff capability**:
- Resources to be added
- Resources to be modified (with property-level changes)
- Resources to be deleted
- Replacement behavior (in-place vs recreate)

---

## Known Limitations

### In Scope (wetwire-aws addresses)

| Limitation | How Addressed |
|------------|---------------|
| **Dependency ordering** | Automatic from `ref()` / `get_att()` analysis |
| **Reference validation** | Validate targets exist at build time |
| **Type safety** | Generated classes with typed properties |
| **IDE support** | Type stub generation |
| **Enum constants** | Generated from botocore |

### Out of Scope (AWS CloudFormation issues)

| Limitation | Notes |
|------------|-------|
| **Deployment failures** | CloudFormation handles rollback |
| **Drift detection** | Use `aws cloudformation detect-stack-drift` |
| **Stack policies** | User configures via AWS CLI |
| **Nested stacks** | Supported via template composition |

**Philosophy:** wetwire-aws generates valid CloudFormation JSON. What happens after deployment is CloudFormation's responsibility.

---

## AWS IaC Landscape (2025)

### Current State

| Tool | Status | AWS Position |
|------|--------|--------------|
| **CloudFormation** | Foundation | Native, fully supported |
| **CDK** | **Recommended** | AWS's preferred high-level IaC |
| **SAM** | Active | Serverless-focused, compiles to CF |
| **Terraform** | Popular | Supported via AWS provider |

### AWS's Strategic Direction

AWS continues to invest in CloudFormation as the foundation:
- CDK compiles to CloudFormation
- SAM compiles to CloudFormation
- CloudFormation receives continuous updates
- Change Sets provide native diff capability

**The substrate is solid.** CloudFormation is not going away - it's the foundation for AWS's IaC ecosystem.

---

## Alternative Output Formats

| Format | Method | Use Case |
|--------|--------|----------|
| **CloudFormation JSON** (primary) | `template.to_json()` | Standard AWS deployments |
| CloudFormation YAML | `template.to_yaml()` | Human-readable alternative |
| SAM Template | `template.to_sam()` | Serverless applications |

**Priority:** JSON is the primary format. YAML is trivial (same structure, different serialization). SAM requires `Transform` header and follows SAM resource conventions.

---

## Viability Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| Schema source | **Good** | CF Spec + botocore (two sources) |
| Resource coverage | **Excellent** | All CF resource types (~800) |
| Reference pattern | **Excellent** | `ref()` / `get_att()` → Ref/GetAtt |
| Dependency handling | **Excellent** | Automatic from intrinsic analysis |
| Diff capability | **Excellent** | Native Change Sets |
| State management | **Excellent** | CloudFormation handles this |
| Deploy tooling | **Excellent** | Native AWS CLI |
| No external deps | **Yes** | Just AWS CLI |

### Value Proposition

**wetwire-aws adds value as a synthesis library by:**
1. **Type-safe authoring** - IDE autocomplete, type stubs
2. **Build-time validation** - Catch `ref()` errors before deployment
3. **Cleaner API** - Decorated classes vs raw JSON/YAML
4. **Enum constants** - Type-safe values from botocore
5. **Auto-discovery** - Resources register automatically

**What it does NOT do:**
- Deploy stacks (use `aws cloudformation deploy`)
- Create change sets (use `aws cloudformation create-change-set`)
- Manage state (CloudFormation handles this)
- Detect drift (use `aws cloudformation detect-stack-drift`)

---

## Cross-Cloud Comparison

| Aspect | wetwire-aws | wetwire-gcp | wetwire-azure |
|--------|-------------|-------------|---------------|
| **Schema source** | CF Spec + botocore | Config Connector CRDs | ARM schemas |
| **Unified source** | No (two sources) | Yes | Yes |
| **Output format** | CloudFormation JSON | Config Connector YAML | ARM JSON |
| **Deploy tool** | `aws cloudformation` | `kubectl apply` | `az deployment` |
| **Diff tool** | Change Sets (native) | `kubectl diff` | `what-if` (native) |
| **Diff quality** | Excellent | Adequate | Excellent |
| **Bootstrap requirement** | None | K8s cluster | None |
| **Deletion ordering** | Automatic (from Ref) | Manual (needs annotations) | Automatic (from resourceId) |
| **External deps** | AWS CLI only | Kubernetes cluster | Azure CLI only |
| **State** | CloudFormation | Kubernetes API | Azure RM |
| **Reconciliation** | Manual re-deploy | Continuous | Manual re-deploy |
| **Resource count** | ~800 types | 452 CRDs | ~1200 types |

### Key Insights

1. **AWS and Azure have native diff** (Change Sets, what-if). GCP relies on `kubectl diff`.

2. **AWS and Azure are most similar** - both use native CLI, native diff, no Kubernetes.

3. **GCP requires Kubernetes** - the Config Connector path requires a K8s cluster.

4. **AWS has the two-source problem** - schema and enums come from different places. GCP and Azure have unified sources.

---

## Conclusion

**Status: Proven viable.**

wetwire-aws demonstrates that **synthesis-only IaC libraries are viable and valuable**:

| Factor | Assessment |
|--------|------------|
| **Schema source** | Good - CF Spec + botocore (two sources) |
| **Output format** | CloudFormation JSON - native AWS |
| **Diff capability** | Excellent - native Change Sets |
| **Deploy tooling** | Excellent - native AWS CLI |
| **Scope clarity** | Synthesis only |

**The key insight:** By limiting scope to synthesis, we avoid the complexity of state management, drift detection, and deployment orchestration - those are handled by CloudFormation.

**This pattern transfers to other domains:**
- GCP: Config Connector YAML output, `kubectl` for deploy/diff
- Azure: ARM JSON output, `az` CLI for deploy, `what-if` for diff
- Kubernetes: K8s YAML output, `kubectl` for deploy/diff
- GitHub Actions: Workflow YAML output, push to trigger

---

## Sources

### CloudFormation
- [CloudFormation Resource Specification](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-resource-specification.html) - Schema source
- [CloudFormation Intrinsic Functions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html) - Ref, GetAtt, Sub, etc.
- [CloudFormation Change Sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html) - Native diff

### botocore
- [botocore](https://github.com/boto/botocore) - AWS SDK core, enum source
- [Service Model Loading](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/loaders.html) - How to extract enums
