# Wetwire Kubernetes Feasibility Study

**Status**: Draft
**Purpose**: Evaluate feasibility of `wetwire-k8s` following the same declarative wrapper pattern as `wetwire-aws`.
**Scope**: **Synthesis only** - generates Kubernetes YAML manifests; does not perform diff/apply.
**Recommendation**: **Proceed** - Kubernetes OpenAPI specs as schema source, K8s YAML as output.

---

## Executive Summary

`wetwire-k8s` is a **synthesis library** - it generates Kubernetes YAML manifests from Python dataclasses. Like `wetwire-aws`, it does not perform deployment operations.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  wetwire-k8s (synthesis)                  External tools (deployment)   │
│                                                                          │
│  K8s OpenAPI Spec → Python Dataclasses → Kubernetes YAML                │
│      (schema)           (authoring)          (output)                   │
│                                                   ↓                      │
│                                           kubectl diff/apply            │
│                                           (user's responsibility)        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why Kubernetes YAML as output:**
- Native tooling (`kubectl` is ubiquitous)
- `kubectl diff` for preview (native, no external tools)
- `kubectl apply` for deployment (declarative, idempotent)
- Works with any Kubernetes cluster (EKS, GKE, AKS, on-prem, local)
- GitOps native (Argo CD, Flux out of the box)

**Unique value over raw YAML:**
- Type-safe resource definitions
- Auto-wired labels and selectors
- Cross-resource references without repetition
- IDE autocomplete for all K8s resources
- Preset patterns for common workloads

---

## Vision

**wetwire-k8s is a synthesis library.** It generates Kubernetes YAML from Python dataclasses. It does not deploy, diff, or manage state - those are the user's responsibility via `kubectl`.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          wetwire-k8s (this project)                      │
│                                                                          │
│   @wetwire_k8s                                                  │
│   class MyApp:                            Manifest.from_registry()       │
│       resource: Deployment                       ↓                       │
│       replicas = 3                        print(manifest.to_yaml())      │
│       image = "nginx:latest"                     ↓                       │
│       port = 80                           Kubernetes YAML                │
├─────────────────────────────────────────────────────────────────────────┤
│                    User's toolchain (external)                           │
│                                                                          │
│   kubectl diff -f output.yaml             # Preview changes              │
│   kubectl apply -f output.yaml            # Deploy                       │
│   kubectl get pods -w                     # Watch status                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**Parallel to other wetwire domains:**

| Aspect | wetwire-aws | wetwire-gcp | wetwire-azure | wetwire-k8s |
|--------|----------------|-----|-------|------------|
| **Scope** | Synthesis only | Synthesis only | Synthesis only | Synthesis only |
| **Output** | CF JSON | Config Connector YAML | ARM JSON | K8s YAML |
| **Deploy** | `aws cloudformation` | `kubectl apply` | `az deployment` | `kubectl apply` |
| **Diff** | Change Sets | `kubectl diff` | `what-if` | `kubectl diff` |

**Core principles:**
1. **Synthesis only** - Generate YAML, don't deploy it
2. **Kubernetes OpenAPI as source** - Official K8s schemas for all resources
3. **Declarative wrapper pattern** - Same `@wetwire` approach
4. **Auto-wiring** - Labels, selectors, and references handled automatically

---

## The Problem With Raw Kubernetes YAML

### Verbosity and Repetition

A simple web deployment requires 40+ lines with repeated values:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  labels:
    app: my-app           # Repeated
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app         # Must match template labels exactly
  template:
    metadata:
      labels:
        app: my-app       # Must match selector exactly
    spec:
      containers:
      - name: my-app      # Repeated again
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: my-app-service
spec:
  selector:
    app: my-app           # Must match deployment labels exactly
  ports:
  - port: 80
    targetPort: 80
```

**Pain points:**
- `app: my-app` repeated 4 times
- Selector/label mismatch is a silent failure
- No type checking on port numbers, resource limits, etc.
- No IDE autocomplete for valid fields

### The Vision

```
@wetwire_k8s
class MyApp:
    resource: Deployment
    replicas = 3
    image = "nginx:latest"
    container_port = 80

@wetwire_k8s
class MyAppService:
    resource: Service
    target = MyApp          # Auto-wires selector to MyApp's labels
    port = 80
```

- Labels auto-generated from class name
- Selectors auto-wired from references
- Type-safe port definitions
- 6 lines instead of 40+

---

## Schema Source: Kubernetes OpenAPI Specification

### The Source of Truth

Kubernetes publishes OpenAPI v2/v3 specifications for all built-in resources:

```
https://raw.githubusercontent.com/kubernetes/kubernetes/master/api/openapi-spec/swagger.json
```

Each Kubernetes version has its own spec, containing:
- All resource kinds (Deployment, Service, Pod, etc.)
- All fields with types
- Validation rules (required fields, enums, patterns)
- Documentation strings

### Alternative: kubernetes-client schemas

The official Python client publishes typed models:

```
https://github.com/kubernetes-client/python/tree/master/kubernetes/client/models
```

These are already Python classes but use the imperative pattern, not dataclasses.

### Comparison to Other Schema Sources

| Library | Schema Source | Format |
|---------|---------------|--------|
| wetwire-aws | AWS CF Spec | JSON |
| wetwire-gcp | Config Connector CRDs | YAML |
| wetwire-azure | ARM schemas | JSON |
| **wetwire-k8s** | **K8s OpenAPI** | **JSON (Swagger)** |

---

## The `ref()` Pattern: Label and Selector Wiring

### The K8s Reference Model

Kubernetes uses **label selectors** for loose coupling between resources:

```yaml
# Service selects Pods by labels
spec:
  selector:
    app: my-app  # Matches pods with this label

# Deployment creates Pods with labels
spec:
  template:
    metadata:
      labels:
        app: my-app  # Label that Service selects
```

### Mapping to wetwire-k8s

```
@wetwire_k8s
class MyApp:
    resource: Deployment
    image = "nginx:latest"
    # Labels auto-generated: {"app": "my-app"}

@wetwire_k8s
class MyAppService:
    resource: Service
    target = MyApp  # → selector: {app: my-app}
    port = 80
```

The `target = MyApp` reference:
1. Extracts `MyApp`'s auto-generated labels
2. Generates `spec.selector` with those labels
3. Creates an implicit dependency

### Reference Types in Kubernetes

| Pattern | Example | Generated |
|---------|---------|-----------|
| Service → Deployment | `target = MyDeployment` | `selector: {app: my-deployment}` |
| Ingress → Service | `backend = MyService` | `service.name: my-service` |
| PVC → StorageClass | `storage_class = MyStorageClass` | `storageClassName: my-storage-class` |
| Pod → ConfigMap | `config = MyConfigMap` | `configMapRef.name: my-config-map` |
| Pod → Secret | `secret = MySecret` | `secretRef.name: my-secret` |

### Explicit Labels

When auto-generated labels aren't sufficient:

```
@wetwire_k8s
class MyApp:
    resource: Deployment
    labels = {
        "app": "my-app",
        "version": "v1",
        "team": "platform",
    }
```

---

## Auto-Wiring: Reducing Boilerplate

### What Gets Auto-Wired

| Field | Auto-Generated From |
|-------|---------------------|
| `metadata.name` | Class name (snake_case → kebab-case) |
| `metadata.labels` | `{app: <name>}` by default |
| `spec.selector.matchLabels` | Same as `metadata.labels` |
| `spec.template.metadata.labels` | Same as `metadata.labels` |
| `spec.containers[0].name` | Class name |

### Before and After

**Raw YAML (40 lines):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-frontend
  labels:
    app: nginx-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx-frontend
  template:
    metadata:
      labels:
        app: nginx-frontend
    spec:
      containers:
      - name: nginx-frontend
        image: nginx:1.21
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
```

**wetwire-k8s (10 lines):**
```
@wetwire_k8s
class NginxFrontend:
    resource: Deployment
    replicas = 3
    image = "nginx:1.21"
    container_port = 80
    resources = Resources(
        requests={"memory": "64Mi", "cpu": "250m"},
        limits={"memory": "128Mi", "cpu": "500m"},
    )
```

---

## User Workflow

wetwire-k8s generates YAML. The user handles diff and deploy:

```bash
# 1. Generate Kubernetes YAML (wetwire-k8s)
python -m my_app > manifests.yaml

# 2. Preview changes (kubectl - external)
kubectl diff -f manifests.yaml

# 3. Apply changes (kubectl - external)
kubectl apply -f manifests.yaml

# 4. Watch rollout (kubectl - external)
kubectl rollout status deployment/my-app
```

### Multi-Environment Support

```
# environments.py
from wetwire.k8s import Namespace

@wetwire_k8s
class Production(Namespace):
    name = "production"

@wetwire_k8s
class Staging(Namespace):
    name = "staging"

# app.py
@wetwire_k8s
class MyApp:
    resource: Deployment
    namespace = Production  # or Staging
    replicas = when(namespace == Production, 3, else_=1)
```

### Kustomize Integration

Generated YAML works with Kustomize for environment overlays:

```bash
python -m my_app > base/deployment.yaml
kubectl apply -k overlays/production/
```

---

## Known Limitations

### In Scope (wetwire-k8s can address)

| Limitation | Mitigation |
|------------|------------|
| **CRD support** | Parse CRD schemas, generate types dynamically |
| **Helm chart generation** | Output Helm templates with `{{ .Values }}` |
| **Label validation** | Validate label key/value format at build time |

### Out of Scope (kubectl / cluster issues)

| Limitation | Notes |
|------------|-------|
| **Admission webhooks** | Cluster may reject valid YAML; not our problem |
| **CRD availability** | User must install CRDs before applying; not our problem |
| **RBAC** | Permission errors are runtime; not our problem |

**Philosophy:** wetwire-k8s generates valid Kubernetes YAML. What happens after `kubectl apply` is Kubernetes' responsibility.

---

## Comparison to Existing Tools

### cdk8s

AWS's CDK for Kubernetes:

```
# cdk8s - imperative, construct pattern
from cdk8s_plus_26 import Deployment

deployment = Deployment(self, "MyApp",
    replicas=3,
    containers=[Container(image="nginx")]
)
```

**Differences:**
- cdk8s uses CDK construct pattern (imperative)
- wetwire-k8s uses flat wrapper pattern (declarative)
- cdk8s requires `cdk8s synth` step
- wetwire-k8s is just Python → YAML

### Helm

Templating engine:

```yaml
# values.yaml
replicaCount: 3
image: nginx

# deployment.yaml
replicas: {{ .Values.replicaCount }}
image: {{ .Values.image }}
```

**Differences:**
- Helm is text templating, not type-safe
- Helm has package management (charts)
- wetwire-k8s is type-safe Python

### Kustomize

Overlay/patch system:

```yaml
# kustomization.yaml
resources:
  - deployment.yaml
patches:
  - replica_count.yaml
```

**Differences:**
- Kustomize operates on existing YAML
- wetwire-k8s generates YAML
- They can work together: generate base, kustomize overlays

### Pulumi Kubernetes

```
# Pulumi - imperative
deployment = k8s.apps.v1.Deployment("my-app",
    spec=k8s.apps.v1.DeploymentSpecArgs(
        replicas=3,
        ...
    )
)
```

**Differences:**
- Pulumi is imperative with state management
- wetwire-k8s is declarative, stateless synthesis

---

## Proposed Package Structure

```
wetwire-k8s/
├── specs/
│   └── kubernetes-openapi/          # Downloaded K8s OpenAPI specs
│       ├── v1.28.json
│       ├── v1.29.json
│       └── v1.30.json
├── src/wetwire_k8s/
│   ├── core/
│   │   ├── base.py                  # KubernetesResource base class
│   │   ├── manifest.py              # Manifest.from_registry()
│   │   ├── labels.py                # Label auto-generation
│   │   └── selectors.py             # Selector wiring
│   ├── codegen/
│   │   ├── openapi_parser.py        # Parse K8s OpenAPI specs
│   │   └── generator.py             # Generate Python dataclasses
│   └── resources/                   # GENERATED (committed to git)
│       ├── apps/
│       │   ├── deployment.py
│       │   ├── statefulset.py
│       │   ├── daemonset.py
│       │   └── replicaset.py
│       ├── core/
│       │   ├── pod.py
│       │   ├── service.py
│       │   ├── configmap.py
│       │   ├── secret.py
│       │   └── namespace.py
│       ├── networking/
│       │   ├── ingress.py
│       │   └── networkpolicy.py
│       ├── batch/
│       │   ├── job.py
│       │   └── cronjob.py
│       └── ...
├── scripts/
│   ├── regenerate.sh
│   └── download_specs.sh
└── pyproject.toml
```

---

## Implementation Path

### Phase 1: Core Resources + Proof of Concept

- Download Kubernetes OpenAPI spec for v1.28+
- Parse spec for core resources (Deployment, Service, Pod, ConfigMap)
- Generate Python dataclasses with type annotations
- Implement auto-wiring for labels and selectors
- Verify synthesis: Python → valid K8s YAML

### Phase 2: Full Resource Coverage

- Generate all built-in K8s resources (~60 kinds)
- Implement `ref()` patterns for all cross-resource references
- Add namespace support
- Generate `.pyi` stubs for IDE support

### Phase 3: Advanced Features

- CRD support (parse arbitrary CRDs, generate types)
- Preset patterns (`WebService`, `CronJob`, `StatefulApp`)
- Multi-environment support
- Helm template output option
- CLI tooling (`wetwire init --domain k8s`, `wetwire lint`, `wetwire stubs`)

### Phase 4: Ecosystem Integration

- Kustomize base generation
- Argo CD Application generation
- Flux Kustomization generation

---

## Preset Patterns

Common workload patterns as base classes:

### WebService

```
@wetwire_k8s
class MyAPI(WebService):
    image = "my-api:latest"
    port = 8080
    replicas = 3
    # Generates: Deployment + Service + optional Ingress
```

Expands to:
- Deployment with health checks
- Service (ClusterIP)
- HorizontalPodAutoscaler (optional)

### CronWorkload

```
@wetwire_k8s
class DailyReport(CronWorkload):
    image = "reporter:latest"
    schedule = "0 2 * * *"
    # Generates: CronJob with best practices
```

### StatefulService

```
@wetwire_k8s
class Database(StatefulService):
    image = "postgres:15"
    storage = "10Gi"
    # Generates: StatefulSet + Service + PVC template
```

---

## Viability Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| Schema source | **Excellent** | Official OpenAPI spec, versioned |
| Resource coverage | **Excellent** | All built-in K8s resources |
| Reference pattern | **Good** | Label selectors map to `ref()` |
| Auto-wiring potential | **Excellent** | Labels/selectors/names are repetitive |
| Diff capability | **Good** | `kubectl diff` is native |
| Deploy tooling | **Excellent** | `kubectl apply` is standard |
| Ecosystem | **Excellent** | Works with Helm, Kustomize, GitOps |

### Value Proposition

**wetwire-k8s adds value by:**
1. **Type-safe definitions** — IDE autocomplete, catch errors before apply
2. **Auto-wiring** — Labels, selectors, names derived automatically
3. **Boilerplate reduction** — 10 lines instead of 40
4. **Cross-resource references** — `target = MyDeployment` instead of manual selector copying
5. **Presets** — Common patterns as one-liners
6. **Familiar experience** — Same pattern as wetwire-aws

**What it does NOT do:**
- Deploy resources (use `kubectl apply`)
- Diff changes (use `kubectl diff`)
- Manage state (Kubernetes handles this)
- Replace Helm/Kustomize (works alongside them)

---

## Relationship to Other Wetwire Domains

wetwire-k8s is **complementary** to cloud-specific libraries:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Infrastructure Layer                         │
│                                                                  │
│  wetwire-aws    →  AWS (VPC, RDS, S3, etc.)                     │
│  wetwire-gcp    →  GCP (VPC, Cloud SQL, GCS)                    │
│  wetwire-azure  →  Azure (VNet, SQL, Blob)                      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                     Application Layer                            │
│                                                                  │
│  wetwire-k8s    →  Workloads (Pods, Services)                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Use case:** Define your AWS infrastructure with wetwire-aws, then define the applications running on EKS with wetwire-k8s.

---

## Conclusion

**Recommendation: Proceed with wetwire-k8s.**

| Factor | Assessment |
|--------|------------|
| **Schema source** | Excellent — official OpenAPI specs |
| **Pain point** | Real — K8s YAML is verbose and error-prone |
| **Auto-wiring opportunity** | Excellent — labels/selectors are the #1 pain |
| **Diff/deploy tooling** | Native — `kubectl diff/apply` |
| **Ecosystem fit** | Excellent — works with Helm, Kustomize, GitOps |
| **Differentiation** | Clear — no existing flat dataclass pattern for K8s |

**Unique advantages over existing tools:**
- Flatter than cdk8s (no construct pattern)
- Type-safer than Helm (not text templating)
- Generates for Kustomize (not replaces it)
- Stateless unlike Pulumi

**Next step:** Build Phase 1 proof of concept — parse OpenAPI spec, generate Deployment and Service dataclasses, implement label auto-wiring, synthesize valid K8s YAML.

---

**Part of the Wetwire Framework** — See DRAFT_DECLARATIVE_DATACLASS_FRAMEWORK.md for the universal pattern.

---

## Sources

### Primary
- [Kubernetes OpenAPI Spec](https://github.com/kubernetes/kubernetes/tree/master/api/openapi-spec)
- [Kubernetes API Reference](https://kubernetes.io/docs/reference/kubernetes-api/)
- [kubectl diff documentation](https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#diff)

### Comparison Tools
- [cdk8s](https://cdk8s.io/) — AWS CDK for Kubernetes
- [Helm](https://helm.sh/) — Kubernetes package manager
- [Kustomize](https://kustomize.io/) — Kubernetes native configuration management
- [Pulumi Kubernetes](https://www.pulumi.com/registry/packages/kubernetes/)
