# Graph Refs Specification

**Version:** 0.1
**Status:** Draft
**Last Updated:** 2024-12-26

## Abstract

This document specifies the typing primitives for expressing graph references in dataclass-based DSLs. These types enable static type checkers to verify that resource relationships are correctly typed.

The specification is designed to be implementable as a standalone library (`graph-refs`) with potential inclusion in Python's `typing` module or `typing_extensions`.

---

## 1. Overview

### 1.1 Purpose

Dataclasses naturally model tree-structured data. Many domains require graph structures where objects reference each other. This specification provides type markers that:

1. Enable type checkers to verify reference targets
2. Support IDE autocomplete for valid reference targets
3. Enable static graph analysis (dependency detection, cycle detection)
4. Integrate with `@dataclass_transform` for DSL decorators

### 1.2 Types Defined

| Type | Purpose |
|------|---------|
| `Ref[T]` | Reference to an instance of type T |
| `Attr[T, name]` | Reference to a specific attribute of T |
| `RefList[T]` | List of references to T |
| `RefDict[K, V]` | Dict with reference values |
| `ContextRef[name]` | Reference to a context value |

### 1.3 Functions Defined

| Function | Purpose |
|----------|---------|
| `get_refs(cls)` | Extract reference metadata from a class |
| `get_dependencies(cls)` | Compute dependency graph |

---

## 2. Ref[T] — Typed Reference

### 2.1 Definition

`Ref[T]` represents a reference to an instance of type `T`.

```
from graph_refs import Ref

@dataclass
class Subnet:
    network: Ref[Network]  # Reference to a Network
    cidr: str
```

### 2.2 Type Checker Behavior

`Ref[T]` MUST be assignable from:
- The class `T` itself (for implicit reference patterns)
- An instance of `Ref[T]`
- Any subclass of `T` (covariant)

`Ref[T]` MUST NOT be assignable from:
- Unrelated types
- `str` (unless explicitly typed as `Ref[T] | str`)

```
subnet = Subnet(network=MyNetwork)      # OK — class reference
subnet = Subnet(network=MyBucket)       # Type error — Bucket is not Network
```

### 2.3 Runtime Representation

At runtime, `Ref[T]` is a generic alias. The type parameter is available via introspection:

```
from typing import get_origin, get_args

field_type = Ref[Network]
get_origin(field_type)  # Ref
get_args(field_type)    # (Network,)
```

### 2.4 Implementation

```
from typing import Generic, TypeVar

T = TypeVar("T")

class Ref(Generic[T]):
    """A typed reference to another class."""
    __slots__ = ()

    def __class_getitem__(cls, item):
        return _GenericAlias(cls, (item,))
```

---

## 3. Attr[T, name] — Typed Attribute Reference

### 3.1 Definition

`Attr[T, name]` represents a reference to a specific attribute of type `T`.

```
from graph_refs import Attr
from typing import Literal

@dataclass
class Function:
    role_arn: Attr[Role, Literal["Arn"]]  # Reference to Role's Arn attribute
```

### 3.2 Shorthand Syntax

For convenience, string literals MAY be used directly:

```
role_arn: Attr[Role, "Arn"]  # Equivalent to Attr[Role, Literal["Arn"]]
```

### 3.3 Type Checker Behavior

`Attr[T, Literal["name"]]` MUST be assignable from:
- `T.name` (class attribute access)
- An instance of `Attr[T, Literal["name"]]`

Type checkers SHOULD verify that `T` has an attribute named `name`.

```
function = Function(role_arn=MyRole.Arn)     # OK
function = Function(role_arn=MyRole.Xyz)     # Type error — no Xyz attribute
function = Function(role_arn=MyBucket.Arn)   # Type error — expected Role
```

### 3.4 Implementation

```
from typing import Generic, TypeVar

T = TypeVar("T")
NameT = TypeVar("NameT")

class Attr(Generic[T, NameT]):
    """A typed reference to an attribute of another class."""
    __slots__ = ()

    def __class_getitem__(cls, args):
        if not isinstance(args, tuple) or len(args) != 2:
            raise TypeError("Attr requires exactly two arguments")
        return _GenericAlias(cls, args)
```

---

## 4. RefList[T] and RefDict[K, V] — Collection Types

### 4.1 Definition

Collection types for references:

```
from graph_refs import RefList, RefDict

@dataclass
class LoadBalancer:
    targets: RefList[Instance]           # list[Ref[Instance]]
    mappings: RefDict[str, TargetGroup]  # dict[str, Ref[TargetGroup]]
```

### 4.2 Equivalence

These are semantic aliases:
- `RefList[T]` ≡ `list[Ref[T]]`
- `RefDict[K, V]` ≡ `dict[K, Ref[V]]`

### 4.3 Purpose

1. **Conciseness**: `RefList[T]` vs `list[Ref[T]]`
2. **Signaling**: Indicates the decorator should process elements for implicit reference conversion

### 4.4 Implementation

```
from typing import Generic, TypeVar

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

class RefList(Generic[T]):
    """Semantic alias for list[Ref[T]]."""
    __slots__ = ()

class RefDict(Generic[K, V]):
    """Semantic alias for dict[K, Ref[V]]."""
    __slots__ = ()
```

---

## 5. ContextRef[name] — Context Reference

### 5.1 Definition

`ContextRef[name]` represents a reference to a context value resolved at serialization time.

```
from graph_refs import ContextRef
from typing import Literal

@dataclass
class MyResource:
    name: ContextRef[Literal["project"]]   # Resolved from context.project
    region: ContextRef[Literal["region"]]  # Resolved from context.region
```

### 5.2 Distinction from Ref

Context references are distinct from resource references:
- `Ref[T]` references another resource in the graph
- `ContextRef[name]` references an environment/context value

### 5.3 Implementation

```
from typing import Generic, TypeVar

NameT = TypeVar("NameT")

class ContextRef(Generic[NameT]):
    """A typed reference to a context value."""
    __slots__ = ()

    def __class_getitem__(cls, item):
        return _GenericAlias(cls, (item,))
```

---

## 6. RefInfo — Reference Metadata

### 6.1 Definition

`RefInfo` is a dataclass containing metadata about a reference field.

```
from dataclasses import dataclass

@dataclass(frozen=True)
class RefInfo:
    field: str           # Field name
    target: type         # Referenced class
    attr: str | None     # Attribute name (for Attr types)
    is_list: bool        # True if RefList
    is_dict: bool        # True if RefDict
    is_optional: bool    # True if Optional[Ref[T]]
    is_context: bool     # True if ContextRef
```

### 6.2 Usage

`RefInfo` is returned by `get_refs()` and enables:
- Dependency graph construction
- Serialization logic
- Validation tools

---

## 7. get_refs() — Reference Introspection

### 7.1 Signature

```
def get_refs(cls: type) -> dict[str, RefInfo]:
    """Extract reference information from a class.

    Args:
        cls: The class to analyze

    Returns:
        Dict mapping field names to RefInfo
    """
```

### 7.2 Behavior

`get_refs()` MUST:
1. Inspect type hints using `get_type_hints(cls)`
2. Identify fields annotated with `Ref`, `Attr`, `RefList`, `RefDict`, `ContextRef`
3. Handle `Optional[Ref[T]]` (Union with None)
4. Return a dict of `RefInfo` for each reference field

### 7.3 Example

```
@dataclass
class Subnet:
    network: Ref[Network]
    gateway: Ref[Gateway]
    cidr: str

refs = get_refs(Subnet)
# Returns:
# {
#     'network': RefInfo(field='network', target=Network, attr=None, ...),
#     'gateway': RefInfo(field='gateway', target=Gateway, attr=None, ...),
# }
# Note: 'cidr' is not included (not a reference type)
```

### 7.4 Implementation

```
from typing import get_type_hints, get_origin, get_args, Union

def get_refs(cls: type) -> dict[str, RefInfo]:
    refs = {}
    try:
        hints = get_type_hints(cls)
    except Exception:
        return refs

    for name, hint in hints.items():
        origin = get_origin(hint)
        args = get_args(hint)

        # Handle Optional (Union with None)
        is_optional = False
        if origin is Union:
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                is_optional = True
                hint = non_none[0]
                origin = get_origin(hint)
                args = get_args(hint)

        if origin is Ref and args:
            refs[name] = RefInfo(
                field=name,
                target=args[0],
                attr=None,
                is_list=False,
                is_dict=False,
                is_optional=is_optional,
                is_context=False,
            )
        elif origin is Attr and len(args) >= 2:
            refs[name] = RefInfo(
                field=name,
                target=args[0],
                attr=_extract_literal(args[1]),
                is_list=False,
                is_dict=False,
                is_optional=is_optional,
                is_context=False,
            )
        elif origin is RefList and args:
            refs[name] = RefInfo(
                field=name,
                target=args[0],
                attr=None,
                is_list=True,
                is_dict=False,
                is_optional=is_optional,
                is_context=False,
            )
        elif origin is RefDict and len(args) >= 2:
            refs[name] = RefInfo(
                field=name,
                target=args[1],
                attr=None,
                is_list=False,
                is_dict=True,
                is_optional=is_optional,
                is_context=False,
            )
        elif origin is ContextRef and args:
            refs[name] = RefInfo(
                field=name,
                target=type(None),
                attr=_extract_literal(args[0]),
                is_list=False,
                is_dict=False,
                is_optional=is_optional,
                is_context=True,
            )

    return refs


def _extract_literal(hint) -> str | None:
    """Extract string value from Literal type."""
    origin = get_origin(hint)
    if origin is Literal:
        args = get_args(hint)
        if args and isinstance(args[0], str):
            return args[0]
    if isinstance(hint, str):
        return hint
    return None
```

---

## 8. get_dependencies() — Dependency Graph

### 8.1 Signature

```
def get_dependencies(cls: type, transitive: bool = False) -> set[type]:
    """Compute dependency set from reference information.

    Args:
        cls: The class to analyze
        transitive: If True, include dependencies of dependencies

    Returns:
        Set of classes this class depends on
    """
```

### 8.2 Behavior

`get_dependencies()` MUST:
1. Call `get_refs(cls)` to get reference information
2. Extract target types from non-context references
3. If `transitive=True`, recursively include nested dependencies

### 8.3 Example

```
@dataclass
class Network:
    cidr: str

@dataclass
class Subnet:
    network: Ref[Network]
    cidr: str

@dataclass
class Instance:
    subnet: Ref[Subnet]
    name: str

get_dependencies(Instance)
# Returns: {Subnet}

get_dependencies(Instance, transitive=True)
# Returns: {Subnet, Network}
```

### 8.4 Implementation

```
def get_dependencies(cls: type, transitive: bool = False) -> set[type]:
    refs = get_refs(cls)
    deps = {
        info.target
        for info in refs.values()
        if not info.is_context and info.target is not type(None)
    }

    if transitive:
        visited = set()
        to_visit = list(deps)
        while to_visit:
            current = to_visit.pop()
            if current not in visited:
                visited.add(current)
                nested = get_dependencies(current, transitive=False)
                to_visit.extend(nested - visited)
        return visited

    return deps
```

---

## 9. Type Checker Integration

### 9.1 @dataclass_transform Extensions

For DSL decorators, this specification proposes extensions to `@dataclass_transform`:

#### ref_types Parameter

```
@dataclass_transform(
    ref_types=(Ref, Attr),  # Types to treat as references
)
def infrastructure(cls):
    ...
```

#### implicit_refs Parameter

```
@dataclass_transform(
    implicit_refs=True,  # Enable no-parens pattern
)
def infrastructure(cls):
    ...
```

When `implicit_refs=True`, type checkers SHOULD:
1. Infer `Ref[T]` when a class `T` is assigned to a field
2. Infer `Attr[T, name]` when `T.name` is assigned to a field
3. Process list/dict literals for nested references

### 9.2 Variance

`Ref[T]` SHOULD be covariant: a `Ref[Dog]` is a `Ref[Animal]`.

---

## 10. Public API

### 10.1 Exports

```
# graph_refs/__init__.py

from graph_refs._types import (
    Ref,
    Attr,
    RefList,
    RefDict,
    ContextRef,
)

from graph_refs._introspection import (
    get_refs,
    get_dependencies,
    RefInfo,
)

__all__ = [
    # Types
    "Ref",
    "Attr",
    "RefList",
    "RefDict",
    "ContextRef",
    # Introspection
    "get_refs",
    "get_dependencies",
    "RefInfo",
]
```

### 10.2 Dependencies

The `graph-refs` package MUST have zero runtime dependencies beyond the Python standard library.

---

## 11. Conformance

### 11.1 Required

Implementations MUST provide:
- `Ref[T]` type with correct generic behavior
- `Attr[T, name]` type with correct generic behavior
- `get_refs()` function
- `RefInfo` dataclass

### 11.2 Optional

Implementations MAY provide:
- `RefList[T]` and `RefDict[K, V]`
- `ContextRef[name]`
- `get_dependencies()`
- `@dataclass_transform` extensions

---

## Appendix A: Complete Example

```
from dataclasses import dataclass
from graph_refs import Ref, Attr, RefList, get_refs, get_dependencies

@dataclass
class VPC:
    cidr: str

@dataclass
class SecurityGroup:
    vpc: Ref[VPC]
    name: str

@dataclass
class Subnet:
    vpc: Ref[VPC]
    cidr: str

@dataclass
class Instance:
    subnet: Ref[Subnet]
    security_groups: RefList[SecurityGroup]
    role_arn: Attr[Role, "Arn"]
    name: str

# Introspection
refs = get_refs(Instance)
# {
#     'subnet': RefInfo(field='subnet', target=Subnet, ...),
#     'security_groups': RefInfo(field='security_groups', target=SecurityGroup, is_list=True, ...),
#     'role_arn': RefInfo(field='role_arn', target=Role, attr='Arn', ...),
# }

deps = get_dependencies(Instance, transitive=True)
# {Subnet, SecurityGroup, VPC, Role}
```

---

## Appendix B: Related Specifications

- [WETWIRE_SPEC.md](WETWIRE_SPEC.md) — Full pattern specification
- [PEP_TYPING.md](../peps/PEP_TYPING.md) — PEP draft for typing extensions
