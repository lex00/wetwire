# Python-Go Naming Alignment

**Status**: Deferred (Go implementation first)
**Purpose**: Document plan to align Python property type naming with Go pattern.

---

## Current State

### Go (implemented)
```
ec2.SecurityGroup_Ingress
ec2.SecurityGroup_Egress
ec2.Instance_BlockDeviceMapping
```

- Uses underscore separator: `{Resource}_{PropertyType}`
- Matches CloudFormation spec naming (PascalCase)
- One file per resource: `security_group_types.go`

### Python (current)
```
ec2.security_group.Ingress
ec2.security_group.Egress
ec2.instance.BlockDeviceMapping
```

- Uses module hierarchy: `{service}.{resource_snake}.{PropertyType}`
- Mixed case: snake_case module, PascalCase class
- One file per resource: `security_group.py`

---

## Proposed Change

Align Python naming with Go pattern for consistency:

| Current Python | Proposed Python | Go |
|----------------|-----------------|-----|
| `ec2.security_group.Ingress` | `ec2.SecurityGroup_Ingress` | `ec2.SecurityGroup_Ingress` |
| `ec2.security_group.Egress` | `ec2.SecurityGroup_Egress` | `ec2.SecurityGroup_Egress` |
| `s3.bucket.VersioningConfiguration` | `s3.Bucket_VersioningConfiguration` | `s3.Bucket_VersioningConfiguration` |

### Benefits

1. **Spec alignment**: Matches CloudFormation resource specification exactly
2. **Cross-language consistency**: Same type names in Python and Go
3. **Simpler imports**: `from wetwire_aws.resources.ec2 import SecurityGroup_Ingress`
4. **Agent-friendly**: Agents can use same type names across languages

### File Structure (unchanged)

Keep separate files per resource in both languages:

```
# Python
resources/ec2/
├── security_group.py      # SecurityGroup + SecurityGroup_Ingress, SecurityGroup_Egress
├── instance.py            # Instance + Instance_BlockDeviceMapping, etc.
└── __init__.py

# Go
resources/ec2/
├── security_group.go           # SecurityGroup resource
├── security_group_types.go     # SecurityGroup_Ingress, SecurityGroup_Egress
├── instance.go                 # Instance resource
├── instance_types.go           # Instance_BlockDeviceMapping, etc.
└── types.go                    # Shared Tag type
```

---

## Implementation Plan

1. Update Python codegen to use `{Resource}_{PropertyType}` naming
2. Update imports in generated code
3. Update examples and tests
4. Update documentation

---

## Migration

This is a breaking change for Python users. Options:

1. **Major version bump**: Release as wetwire-aws 2.0
2. **Deprecation period**: Keep old names as aliases for one release
3. **Import aliases**: Provide compatibility shim module

---

## IAM Policy Document Typing

### PolicyDocument and PolicyStatement

Both implementations provide typed structs:

| Feature | Python | Go |
|---------|--------|-----|
| `PolicyDocument` | dataclass | struct |
| `PolicyStatement` | dataclass | struct |
| `DenyStatement` | dataclass (Effect="Deny") | struct (Effect="Deny") |

### Principal Field

**Python**: Uses raw dicts
```python
principal = {'Service': ['lambda.amazonaws.com']}
principal = {'AWS': '*'}
```

**Go**: Uses typed helpers (Go-specific improvement)
```go
Principal: ServicePrincipal{"lambda.amazonaws.com"}
Principal: AWSPrincipal{"*"}
Principal: FederatedPrincipal{"cognito-identity.amazonaws.com"}
```

**Rationale**: Principal has only 3 possible keys (Service, AWS, Federated). Typed helpers provide:
- Type safety (can't misspell "Service")
- Auto-handling of single value vs array via MarshalJSON
- Cleaner syntax

### Condition Field

**Python**: String constants for operators, raw dicts for structure
```python
from wetwire_aws.constants import BOOL, STRING_EQUALS

condition = {
    BOOL: {'aws:SecureTransport': False},
}
```

**Go**: String constants for operators, `Json` type alias for structure
```go
Condition: Json{
    Bool: Json{"aws:SecureTransport": false},
}
```

**Rationale**: Condition has 20+ operators. Constants prevent typos; typed helpers would be excessive.

### Why Principal is Typed but Condition Uses Constants

| Aspect | Principal | Condition |
|--------|-----------|-----------|
| Number of keys | 3 | 20+ |
| Typed helpers? | Yes (Go) | No (both) |
| Constants? | N/A | Yes (both) |

The inconsistency is acceptable:
1. Principal's 3 keys justify dedicated types
2. Condition's 20+ operators are better served by constants
3. Intrinsic functions (Ref, Sub, GetAtt) are already typed

### Json Type Alias (Go-only)

```go
type Json = map[string]any
```

Shorthand for inline JSON, particularly in Condition blocks. Python doesn't need this since dict literals are already concise.

---

## List Helper (Go-only)

Go requires explicit slice type annotations in composite literals:
```go
Actions: []elasticloadbalancingv2.ListenerRule_Action{ActionForward},
```

The `List` generic helper avoids this verbosity:
```go
Actions: List(ActionForward),
Origins: List(Origin1, Origin2),
```

**Implementation:**
```go
func List[T any](items ...T) []T {
    return items
}
```

Python doesn't need this since list literals are already concise: `[item1, item2]`.

---

## Typing Principles

1. **Type everything we can** with names close to the CF spec
2. **Use constants** when there are many options (20+)
3. **Use typed helpers** when there are few options (3-5) and they're frequently used
4. **Use Json alias** (Go) for arbitrary nested structures
5. **Use List helper** (Go) to avoid verbose slice type annotations
