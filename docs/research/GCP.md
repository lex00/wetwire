# Wetwire GCP Feasibility Study

**Status**: Draft
**Purpose**: Evaluate feasibility of `wetwire-gcp` following the same declarative wrapper pattern as `wetwire-aws`.
**Scope**: **Synthesis only** - generates Config Connector YAML; does not perform diff/apply.
**Recommendation**: **Proceed with KRM path** - Config Connector CRDs as schema source, Config Connector YAML as output.

---

## Executive Summary

`wetwire-gcp` is a **synthesis library** - it generates Config Connector YAML from Python dataclasses. Like `wetwire-aws`, it does not perform deployment operations.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  wetwire-gcp (synthesis)                  External tools (deployment)   │
│                                                                          │
│  Config Connector CRDs → Python Dataclasses → Config Connector YAML     │
│        (schema)              (authoring)           (output)              │
│                                                        ↓                 │
│                                                 kubectl diff/apply       │
│                                                 (user's responsibility)  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why Config Connector YAML as output:**
- No Terraform dependency (`kubectl` is ubiquitous)
- Diff via `kubectl diff` (adequate, improving)
- Continuous drift reconciliation (superior to point-in-time)
- GitOps native (Argo CD, Flux out of the box)
- Aligns with Google's strategic direction (KRM)

**Trade-offs accepted:**
- `kubectl diff` less polished than `terraform plan` or AWS Change Sets
- Requires Kubernetes cluster with Config Connector (most GCP shops have GKE)

---

## Vision

**wetwire-gcp is a synthesis library.** It generates Config Connector YAML from Python dataclasses. It does not deploy, diff, or manage state - those are the user's responsibility via `kubectl`.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         wetwire-gcp (this project)                       │
│                                                                          │
│   @wetwire_gcp                                                           │
│   class MyInstance:                     Template.from_registry()         │
│       resource: compute.ComputeInstance        ↓                         │
│       machineType = "e2-medium"         print(template.to_yaml())        │
│       networkRef = ref(MyNetwork)              ↓                         │
│                                         Config Connector YAML            │
├─────────────────────────────────────────────────────────────────────────┤
│                    User's toolchain (external)                           │
│                                                                          │
│   kubectl diff -f output.yaml           # Preview changes                │
│   kubectl apply -f output.yaml          # Deploy                         │
│   kubectl get computeinstance -w        # Watch reconciliation           │
└─────────────────────────────────────────────────────────────────────────┘
```

**Parallel to other wetwire domains:**

| Aspect | wetwire-aws | wetwire-gcp | wetwire-azure |
|--------|---------------------------|-----------------|-------------------|
| **Scope** | Synthesis only | Synthesis only | Synthesis only |
| **Output** | CloudFormation JSON | Config Connector YAML | ARM JSON |
| **Deploy tool** | `aws cloudformation` | `kubectl apply` | `az deployment` |
| **Diff tool** | Change Sets (native) | `kubectl diff` | `what-if` (native) |

**Core principles:**
1. **Synthesis only** - Generate YAML, don't deploy it
2. **Config Connector as source and target** - CRDs define schema, YAML is output
3. **Declarative wrapper pattern** - Same `@wetwire` approach as wetwire-aws
4. **Python-native experience** - `ref()`, type-safe IDE autocomplete, `.pyi` stubs

---

## Why Config Connector YAML?

### The GCP IaC Landscape

| Tool | Status | Native GCP | Diff Capability |
|------|--------|------------|-----------------|
| **Config Connector** | Growing | Kubernetes-native | `kubectl diff` |
| **Terraform** | Primary | No | `terraform plan` |
| **Deployment Manager** | **Deprecated** | Yes | EOL March 2026 |
| **Crossplane** | CNCF Graduated | Multi-cloud | `kubectl diff` |

### Why Config Connector Wins

**1. No Terraform dependency**

If wetwire-gcp outputs Terraform JSON, users still need `terraform plan` and `terraform apply`. That defeats the purpose - you've added a Python layer without removing the Terraform dependency.

| Output Format | External Tool | Value |
|---------------|---------------|-------|
| Terraform JSON | `terraform` CLI | **Low** - still need TF |
| **Config Connector YAML** | `kubectl` | **High** - no TF needed |
| Direct API | Custom engine | **Highest** - but hard to build |

**2. kubectl is ubiquitous**

| Output Format | External Tool | Native GCP |
|---------------|---------------|------------|
| **Config Connector YAML** | `kubectl` | Kubernetes-native |
| Terraform JSON | `terraform` CLI | No |
| Deployment Manager | `gcloud` | Deprecated |

**3. Google's strategic direction**

Google is betting on **KRM** (Kubernetes Resource Model):
- Deployment Manager deprecated → migrate to Config Connector or Terraform
- [Waze chose Config Connector](https://cloud.google.com/blog/products/containers-kubernetes/infrastructure-as-code-at-waze-using-config-connector) over Terraform
- [Infrastructure Manager](https://cloud.google.com/infrastructure-manager/docs/overview) is Terraform-as-a-Service (not a replacement)

**4. Continuous reconciliation**

Config Connector continuously reconciles desired state with actual state - superior to Terraform's point-in-time model.

---

## Schema Source

### Config Connector CRDs

Config Connector publishes [452 CRD YAML files](https://github.com/GoogleCloudPlatform/k8s-config-connector/tree/master/crds) directly in GitHub:

```
k8s-config-connector/crds/
├── compute_v1beta1_computeinstance.yaml
├── storage_v1beta1_storagebucket.yaml
├── container_v1beta1_containercluster.yaml
├── bigquery_v1beta1_bigquerydataset.yaml
├── sql_v1beta1_sqlinstance.yaml
├── ... (452 files total)
```

Each CRD contains:
- OpenAPI v3 schema (field definitions, types, validation)
- Required vs optional fields
- Enum values (where defined)
- Description/documentation

### The Chain of Truth

```
Magic Modules (Google) → Terraform Provider → Config Connector CRDs
      ↑                                              ↓
  Google's source                             wetwire-gcp source
```

Config Connector CRDs are [generated from Terraform provider schemas](https://github.com/GoogleCloudPlatform/k8s-config-connector/issues/785), which come from Magic Modules.

### Schema Locations

| Source | Location | Format |
|--------|----------|--------|
| Config Connector CRDs | [GitHub](https://github.com/GoogleCloudPlatform/k8s-config-connector/tree/master/crds) | YAML |

### Comparison to CF/Azure

| Aspect | CF Dataclasses | GCP Dataclasses | Azure Dataclasses |
|--------|----------------|-----------------|-------------------|
| Schema source | CF Spec + botocore | Config Connector CRDs | ARM schemas |
| Schema location | AWS CDN + pip | GitHub | GitHub |
| Enum source | botocore (separate) | CRD schemas | ARM schemas |
| Schema format | JSON + Python | YAML | JSON |
| Unified source | No (two sources) | Yes | Yes |
| Resource count | ~800 | 452 CRDs | All Azure resources |

---

## The `ref()` Pattern

Config Connector uses a [consistent reference pattern](https://cloud.google.com/config-connector/docs/how-to/creating-resource-references):

```yaml
# Config Connector YAML
apiVersion: compute.cnrm.cloud.google.com/v1beta1
kind: ComputeInstance
spec:
  networkInterfaceRef:
    name: my-network      # Reference by K8s object name
```

**This maps directly to wetwire-gcp:**

```
from wetwire.gcp import wetwire_gcp, ref
from wetwire.gcp.resources import compute

@wetwire_gcp
class MyNetwork:
    resource: compute.ComputeNetwork
    autoCreateSubnetworks = False

@wetwire_gcp
class MyInstance:
    resource: compute.ComputeInstance
    machineType = "e2-medium"
    networkInterfaceRef = ref(MyNetwork)  # → generates name: "my-network"
```

**Reference types:**
- `name` - Reference K8s object in same namespace
- `namespace` + `name` - Cross-namespace reference
- `external` - Reference resource not managed by Config Connector

---

## Intrinsic Functions

Config Connector YAML doesn't have intrinsic functions like CloudFormation. Values are resolved at build time or via Kubernetes mechanisms.

| Function | wetwire-gcp | Output |
|----------|-----------------|--------|
| `ref(MyNetwork)` | Resource reference | `networkRef: {name: "my-network"}` |
| `GCP_PROJECT` | Context parameter | Resolved at build time |
| `GCP_REGION` | Context parameter | Resolved at build time |
| `GCP_ZONE` | Context parameter | Resolved at build time |

### Context Parameters (Pseudo-Parameters)

| wetwire-gcp | Description |
|-----------------|-------------|
| `GCP_PROJECT` | Project ID |
| `GCP_REGION` | Region (e.g., us-central1) |
| `GCP_ZONE` | Zone (e.g., us-central1-a) |

**Key difference from CF:** GCP context is resolved at build time, not deploy time. This is because Config Connector YAML requires explicit values.

---

## Dependency Handling

Config Connector uses **eventual consistency** rather than explicit ordering:

> "You can create and update resources in any order, regardless of dependency relationships. GKE moves your declared configuration towards eventual consistency."

### How It Works

1. `kubectl apply` all resources simultaneously
2. Config Connector reconciles each resource
3. If dependency missing → retry with exponential backoff (max 2 min)
4. Eventually all resources converge to desired state

### Implication for wetwire-gcp

- Don't need to compute dependency graph for creation
- Can output all resources in a single YAML file
- Config Connector handles retry logic automatically

### Deletion Ordering

Config Connector does **not** handle deletion order. Parent deleted before child → `DeleteFailed` state.

**Mitigation:** wetwire-gcp can generate ArgoCD sync-wave annotations for deletion ordering.

---

## Context Parameters

### CloudFormation Approach

```
from cloudformation_dataclasses.intrinsics import AWS_REGION, AWS_ACCOUNT_ID
region = AWS_REGION  # Resolved by AWS at deploy time
```

### GCP Approach: Explicit Context

GCP requires explicit project/region/zone (resolved at build time):

```
from wetwire.gcp import GCPContext, GCP_PROJECT, GCP_REGION, GCP_ZONE

@dataclass
class GCPContext:
    project: str
    region: str = "us-central1"
    zone: str | None = None

# Usage in resources
@wetwire_gcp
class MyInstance:
    resource: compute.ComputeInstance
    project = GCP_PROJECT  # ContextRef resolved at build time
    zone = GCP_ZONE
    machineType = "e2-medium"

# Build
context = GCPContext(project="my-project-id", region="us-central1")
template = Template.from_registry(context=context)
print(template.to_yaml())  # Config Connector YAML
```

**Note:** The unified `wetwire` package uses `Template` for all providers. `Module` may be provided as an alias in `wetwire-gcp` since Kubernetes manifests aren't traditionally called "templates", but the interface is identical.

```
# These are equivalent:
template = Template.from_registry(context=context)
module = Module.from_registry(context=context)  # Alias
```

---

## User Workflow (External to wetwire-gcp)

wetwire-gcp generates YAML. The user handles diff and deploy with `kubectl`:

```bash
# 1. Generate Config Connector YAML (wetwire-gcp)
python -m my_stack > resources.yaml

# 2. Preview changes (kubectl - external)
kubectl diff -f resources.yaml

# 3. Apply changes (kubectl - external)
kubectl apply -f resources.yaml

# 4. Watch reconciliation (kubectl - external)
kubectl get computeinstance -w
```

### kubectl diff: Realistic Assessment

**Works for most cases:**
```bash
kubectl diff -f resources.yaml
kubectl apply --dry-run=server -f resources.yaml
```

**Known limitations:**
- [Requires write permissions](https://github.com/kubernetes/kubectl/issues/981) (not read-only)
- [Edge cases with removed fields](https://github.com/kubernetes/kubectl/issues/1403)
- Less polished output than `terraform plan` or AWS Change Sets

**Assessment:** Adequate for most use cases. Improving over time. This is outside wetwire-gcp scope - we just generate YAML.

---

## Known Limitations

### In Scope (wetwire-gcp can address)

| Limitation | Mitigation |
|------------|------------|
| **Deletion ordering** | Generate YAML with ArgoCD sync-wave annotations |
| **Reference validation** | Validate `ref()` targets exist at build time |
| **Schema coverage gaps** | Track CRD versions, document gaps |

### Out of Scope (Config Connector / kubectl issues)

| Limitation | Notes |
|------------|-------|
| **Bootstrap problem** | Need K8s cluster first. Use `gcloud` or Terraform for initial cluster. |
| **Immutable fields** | Some changes require delete/recreate. Same as Terraform "forces replacement". |
| **kubectl diff edge cases** | [Write permissions required](https://github.com/kubernetes/kubectl/issues/981), [removed fields not detected](https://github.com/kubernetes/kubectl/issues/1403). Improving over time. |
| **Feature gaps vs Terraform** | 452 CRDs covers most cases. Gap shrinking with active development. |

**Philosophy:** wetwire-gcp generates valid Config Connector YAML. What happens after `kubectl apply` is Config Connector's responsibility.

---

## GCP IaC Landscape (2025)

### Current State

| Tool | Status | Google's Position |
|------|--------|-------------------|
| **Config Connector** | Growing | KRM bet, active development |
| **Terraform** | Primary | Supported via Infrastructure Manager |
| **Deployment Manager** | **Deprecated** | EOL March 2026 |
| **Crossplane** | CNCF Graduated | Multi-cloud alternative |

### Google's Strategic Direction

Google is betting on **KRM** (Kubernetes Resource Model):
- Deployment Manager deprecated → migrate to Config Connector or Terraform
- [Waze chose Config Connector](https://cloud.google.com/blog/products/containers-kubernetes/infrastructure-as-code-at-waze-using-config-connector) over Terraform
- [Infrastructure Manager](https://cloud.google.com/infrastructure-manager/docs/overview) is Terraform-as-a-Service (not a replacement)

**The substrate is solid.** Config Connector is actively maintained, growing, and aligned with Google's strategy.

---

## Alternative Output Formats

| Format | Method | Use Case |
|--------|--------|----------|
| **Config Connector YAML** (primary) | `template.to_yaml()` | Kubernetes-native, no Terraform |
| Terraform JSON | `template.to_terraform()` | Users who prefer Terraform |
| Crossplane CRDs | `template.to_crossplane()` | Multi-cloud Kubernetes |

**Priority:** Config Connector YAML is primary. Alternatives are lower priority.

```
template = Template.from_registry(context=context)

# Primary output
print(template.to_yaml())      # Config Connector YAML

# Alternative outputs
print(template.to_terraform()) # Terraform JSON (requires TF CLI)
print(template.to_crossplane()) # Crossplane CRDs (different schema)
```

**Trade-offs:**
- **Terraform JSON** - Requires Terraform CLI, defeating the no-external-toolchain goal
- **Crossplane CRDs** - Different schema than Config Connector, multi-cloud focused

---

## Proposed Package Structure

```
wetwire-gcp/
├── specs/
│   └── k8s-config-connector/     # Git submodule
│       └── crds/                 # 452 CRD files
├── src/wetwire_gcp/
│   ├── core/
│   │   ├── base.py               # GCPResource base class
│   │   ├── template.py           # Template.from_registry() (Module is alias)
│   │   ├── context.py            # GCPContext, GCP_PROJECT, etc.
│   │   └── intrinsics.py         # ref()
│   ├── codegen/
│   │   ├── crd_parser.py         # Parse CRD YAML schemas
│   │   └── generator.py          # Generate Python dataclasses
│   └── resources/                # GENERATED (committed to git)
│       ├── compute/
│       │   ├── __init__.py
│       │   ├── computeinstance.py
│       │   ├── computenetwork.py
│       │   └── ...
│       ├── storage/
│       ├── container/
│       ├── sql/
│       └── ... (organized by CRD API group)
├── scripts/
│   ├── regenerate.sh             # Parse CRDs, generate code
│   └── update_crds.sh            # git submodule update
└── pyproject.toml
```

---

## Implementation Path

### Phase 1: CRD Parser + Proof of Concept

- Clone [k8s-config-connector](https://github.com/GoogleCloudPlatform/k8s-config-connector) as git submodule
- Parse CRD YAML files from `/crds` directory
- Extract OpenAPI v3 schemas, field types, enums
- Generate Python dataclasses for `compute.ComputeInstance` and `storage.StorageBucket`
- Verify synthesis: Python → Config Connector YAML (valid structure)

### Phase 2: Core Library

- Implement `@wetwire_gcp` decorator
- Implement `ref()` helper → generates `<Kind>Ref.name` in output YAML
- Implement `GCPContext` for project/region/zone resolution
- Implement `Template.from_registry()` → synthesizes Config Connector YAML (`Module` as alias)
- Generate `.pyi` stubs for IDE support

### Phase 3: Production Ready

- Generate all 452 resources from CRDs
- Add ArgoCD sync-wave annotations for deletion ordering
- Validate `ref()` targets at build time
- CLI tooling (`wetwire init --domain gcp`, `wetwire lint`, `wetwire stubs`)
- Documentation and examples

---

## Viability Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| Schema source | **Excellent** | 452 CRDs in GitHub, parseable YAML |
| Resource coverage | **Good** | 200+ GCP services, actively growing |
| Reference pattern | **Excellent** | `<Kind>Ref` maps cleanly to `ref()` |
| Dependency handling | **Good** | Eventual consistency, auto-retry |
| Diff capability | **Adequate** | `kubectl diff` works, has edge cases |
| State management | **Excellent** | No state file, K8s is source of truth |
| Drift correction | **Excellent** | Continuous reconciliation |
| Bootstrap | **Manageable** | Need K8s cluster, most shops have one |
| Deletion ordering | **Weak** | wetwire-gcp can mitigate |

### Value Proposition

**gcp_dataclasses adds value as a synthesis library by:**
1. **Type-safe Python authoring** - IDE autocomplete, `.pyi` stubs
2. **Build-time validation** - Catch `ref()` errors before deployment
3. **Cleaner API** - Python dataclasses vs raw CRD YAML
4. **Deletion ordering** - ArgoCD sync-wave annotations in output
5. **Familiar experience** - Same patterns as cloudformation_dataclasses

**What it does NOT do:**
- Deploy resources (use `kubectl apply`)
- Diff changes (use `kubectl diff`)
- Manage state (Config Connector handles this)
- Reconcile drift (Config Connector handles this)

---

## Cross-Cloud Comparison

| Aspect | wetwire-aws | wetwire-gcp | wetwire-azure |
|--------|----------------|-----------------|-------------------|
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

2. **GCP requires Kubernetes** - the Config Connector path requires a K8s cluster, unlike AWS/Azure.

3. **GCP has continuous reconciliation** - superior to AWS/Azure point-in-time model.

4. **GCP has unified schema source** - unlike CF's two-source problem.

---

## Conclusion

**Recommendation: Proceed with KRM path.**

wetwire-gcp as a **synthesis library** is viable:

| Factor | Assessment |
|--------|------------|
| **Schema source** | Excellent - 452 parseable CRD YAMLs in GitHub |
| **Output format** | Config Connector YAML - kubectl only, no TF |
| **Diff capability** | Adequate - `kubectl diff` works, improving |
| **Deploy tooling** | Good - `kubectl` is ubiquitous |
| **Scope clarity** | Synthesis only, like wetwire-aws |

**The deployment toolchain (kubectl + Config Connector) provides:**
- Diff via `kubectl diff` (adequate)
- Continuous drift reconciliation (superior to AWS/Azure)
- State via Kubernetes API (no state file)

**Accepted trade-offs:**
- `kubectl diff` is adequate, not excellent (out of scope)
- Need K8s cluster for Config Connector (out of scope)
- Some edge cases with immutable fields (out of scope)

**Next step:** Build Phase 1 proof of concept - parse CRDs, generate dataclasses for `ComputeInstance` and `StorageBucket`, synthesize valid Config Connector YAML.

---

**Part of the Wetwire Framework** — See DRAFT_DECLARATIVE_DATACLASS_FRAMEWORK.md for the universal pattern.

---

## Sources

### Primary (Config Connector)
- [Config Connector GitHub](https://github.com/GoogleCloudPlatform/k8s-config-connector) - CRD source files
- [Config Connector Overview](https://cloud.google.com/config-connector/docs/overview) - How it works
- [Config Connector Resources](https://docs.cloud.google.com/config-connector/docs/reference/overview) - 200+ supported resources
- [Creating Resource References](https://cloud.google.com/config-connector/docs/how-to/creating-resource-references) - The `<Kind>Ref` pattern

### Kubernetes Resource Model
- [Build a Platform with KRM](https://cloud.google.com/blog/topics/developers-practitioners/build-platform-krm-part-2-how-kubernetes-resource-model-works) - How KRM works
- [kubectl diff](https://kubernetes.io/blog/2019/01/14/apiserver-dry-run-and-kubectl-diff/) - API server dry-run and diff
- [Waze Config Connector Case Study](https://cloud.google.com/blog/products/containers-kubernetes/infrastructure-as-code-at-waze-using-config-connector) - Real-world adoption

### GCP IaC Ecosystem
- [Infrastructure as Code on Google Cloud](https://docs.cloud.google.com/docs/terraform/iac-overview) - Google's IaC overview
- [Infrastructure Manager](https://cloud.google.com/infrastructure-manager/docs/overview) - Terraform-as-a-Service
- [Deployment Manager Deprecation](https://cloud.google.com/deployment-manager/docs/deprecations) - EOL March 2026
- [Crossplane](https://www.crossplane.io/) - Multi-cloud KRM alternative (CNCF graduated)

### Background (Magic Modules)
- [Magic Modules](https://github.com/GoogleCloudPlatform/magic-modules) - Upstream source for Terraform provider
- [Magic Modules Documentation](https://googlecloudplatform.github.io/magic-modules/) - How resource definitions work
