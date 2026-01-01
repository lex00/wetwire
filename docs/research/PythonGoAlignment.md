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
