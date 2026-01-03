# Wetwire Azure Feasibility Study

**Status**: Draft
**Purpose**: Evaluate feasibility of `wetwire-azure` following the same declarative wrapper pattern as `wetwire-aws`.
**Scope**: **Synthesis only** - generates ARM JSON; does not perform diff/deploy.
**Recommendation**: **Proceed with ARM JSON path** - Azure REST API specs as schema source, ARM JSON as output.

---

## Executive Summary

`wetwire-azure` is a **synthesis library** - it generates ARM JSON from Python dataclasses. Like `wetwire-aws`, it does not perform deployment operations.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  wetwire-azure (synthesis)                External tools (deployment)   │
│                                                                          │
│  Azure REST API Specs → Python Dataclasses → ARM JSON                   │
│        (schema)              (authoring)       (output)                  │
│                                                    ↓                     │
│                                           az deployment what-if/create  │
│                                           (user's responsibility)        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why ARM JSON as output:**
- Native Azure tooling (`az` CLI is ubiquitous)
- **Native what-if** - `az deployment group what-if` (like CloudFormation Change Sets!)
- No external toolchain dependency (Terraform, Kubernetes)
- Microsoft's recommended path (Bicep compiles to ARM JSON)

**Key advantage over GCP:**
Azure has native diff/preview via `what-if`. This makes the ARM path directly analogous to wetwire-aws.

---

## Vision

**wetwire-azure is a synthesis library.** It generates ARM JSON from Python dataclasses. It does not deploy, diff, or manage state - those are the user's responsibility via `az` CLI.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        wetwire-azure (this project)                      │
│                                                                          │
│   @wetwire_azure                                                       │
│   class MyVM:                           Template.from_registry()         │
│       resource: compute.VirtualMachine         ↓                         │
│       vmSize = "Standard_B2s"           print(template.to_json())        │
│       networkInterfaceRef = ref(MyNIC)         ↓                         │
│                                         ARM JSON Template                │
├─────────────────────────────────────────────────────────────────────────┤
│                    User's toolchain (external)                           │
│                                                                          │
│   az deployment group what-if           # Preview changes (native!)      │
│   az deployment group create            # Deploy                         │
│   az resource list                      # View resources                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**Parallel to wetwire-aws:**

| Aspect | wetwire-aws | wetwire-azure |
|--------|---------------------------|-------------------|
| **Scope** | Synthesis only | Synthesis only |
| **Output** | CloudFormation JSON | ARM JSON |
| **Deploy tool** | `aws cloudformation deploy` | `az deployment group create` |
| **Diff tool** | CloudFormation Change Sets | `az deployment what-if` |
| **Native tooling** | Yes (AWS CLI) | Yes (Azure CLI) |

**Core principles:**
1. **Synthesis only** - Generate ARM JSON, don't deploy it
2. **Azure REST API specs as source** - Microsoft's schema for all Azure resources
3. **Declarative wrapper pattern** - Same `@wetwire` approach as wetwire-aws
4. **Python-native experience** - `ref()`, type-safe IDE autocomplete, `.pyi` stubs

---

## Why ARM JSON?

### Why Not Terraform?

**Terraform requires external tooling:**
- Must install Terraform CLI separately
- Terraform manages its own state (not Azure-native)
- Not a native Azure format

### Why Not Azure Service Operator (ASO)?

**ASO requires Kubernetes infrastructure:**
- Must have a running Kubernetes cluster
- Must install ASO controller
- Not as widely deployed as Azure CLI

### Why ARM JSON Wins

**1. Native what-if (like CloudFormation Change Sets)**

```bash
# Preview changes before deployment
az deployment group what-if \
  --resource-group myResourceGroup \
  --template-file template.json
```

This is a **native Azure feature** - no external toolchain required. GCP doesn't have this.

**2. No external dependencies**

| Output Format | External Tool | Native Azure |
|---------------|---------------|--------------|
| **ARM JSON** | `az` CLI | Yes |
| Terraform JSON | `terraform` CLI | No |
| ASO YAML | `kubectl` + K8s cluster | No |

**3. Microsoft's recommended path**

Bicep is Microsoft's recommended IaC language, and it compiles to ARM JSON:
```
Bicep → ARM JSON → Azure Resource Manager
```

By outputting ARM JSON, wetwire-azure integrates with Microsoft's native toolchain.

**4. Direct parallel to wetwire-aws**

| Aspect | wetwire-aws | wetwire-azure |
|--------|----------------|-------------------|
| Output | CF JSON | ARM JSON |
| Deploy | `aws cloudformation` | `az deployment` |
| Diff | Change Sets | `what-if` |
| Native | Yes | Yes |

---

## Schema Source: Azure REST API Specs

### The Chain of Truth

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Microsoft's Schema Sources                            │
│                                                                          │
│   azure-rest-api-specs (OpenAPI/Swagger)                                │
│           ↓                    ↓                    ↓                    │
│   azure-resource-manager-schemas    bicep-types-az    Azure SDKs        │
│           ↓                              ↓                               │
│      ARM JSON schemas              Bicep types                           │
│           ↓                                                              │
│   wetwire-azure (proposed)                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Primary Source: azure-resource-manager-schemas

The [azure-resource-manager-schemas](https://github.com/Azure/azure-resource-manager-schemas) repository contains:
- JSON schemas for all Azure resource types
- Generated automatically from [azure-rest-api-specs](https://github.com/Azure/azure-rest-api-specs)
- Powers VS Code ARM Tools extension
- Hosted at `https://schema.management.azure.com/schemas`

### Alternative: bicep-types-az

The [bicep-types-az](https://github.com/Azure/bicep-types-az) repository:
- Contains Bicep type definitions
- Also generated from azure-rest-api-specs
- Includes property types, enums, and validation rules
- May be easier to parse than JSON schemas

### Comparison to CF/GCP Sources

| Aspect | wetwire-aws | wetwire-gcp | wetwire-azure |
|--------|----------------|-----------------|-------------------|
| Schema source | CF Spec (JSON) | Config Connector CRDs | ARM schemas / bicep-types |
| Schema location | AWS CDN | GitHub (k8s-config-connector) | GitHub (azure-resource-manager-schemas) |
| Schema format | JSON | YAML (CRDs) | JSON |
| Enum source | botocore (separate) | CRD schemas | Same source |
| Generation | Manual spec download | Magic Modules → TF → CRDs | azure-rest-api-specs |

---

## The `ref()` Pattern: ARM Resource References

ARM templates use `resourceId()` and `reference()` functions for cross-resource references:

```json
{
  "type": "Microsoft.Network/networkInterfaces",
  "properties": {
    "ipConfigurations": [{
      "properties": {
        "subnet": {
          "id": "[resourceId('Microsoft.Network/virtualNetworks/subnets', 'myVNet', 'mySubnet')]"
        }
      }
    }]
  }
}
```

**This maps to wetwire-azure:**

```
from wetwire.azure import wetwire_azure, ref
from wetwire.azure.resources import network, compute

@wetwire_azure
class MyVNet:
    resource: network.VirtualNetwork
    addressSpace = {"addressPrefixes": ["10.0.0.0/16"]}

@wetwire_azure
class MySubnet:
    resource: network.VirtualNetworksSubnet
    addressPrefix = "10.0.1.0/24"
    virtualNetworkRef = ref(MyVNet)

@wetwire_azure
class MyNIC:
    resource: network.NetworkInterface
    ipConfigurations = [{
        "subnetRef": ref(MySubnet)  # → generates resourceId() call
    }]
```

**Reference types in ARM:**
- `resourceId()` - Reference to resource ID
- `reference()` - Reference to resource properties (like GetAtt)
- `dependsOn` - Explicit dependency declaration

---

## Intrinsic Functions

ARM templates have a rich set of template functions. wetwire-azure provides Python equivalents:

### Core Functions

| wetwire-azure | ARM Function | Description |
|-------------------|--------------|-------------|
| `ref(Resource)` | `[resourceId(...)]` | Reference to resource ID |
| `reference(Resource, "property")` | `[reference(...).property]` | Get resource property |
| `concat(a, b, c)` | `[concat(a, b, c)]` | String concatenation |
| `format(fmt, args)` | `[format(fmt, args)]` | String formatting |
| `if_(cond, true_val, false_val)` | `[if(cond, true, false)]` | Conditional value |

### Pseudo-Parameters

| wetwire-azure | ARM Function | Description |
|-------------------|--------------|-------------|
| `SUBSCRIPTION_ID` | `[subscription().subscriptionId]` | Current subscription |
| `RESOURCE_GROUP` | `[resourceGroup().name]` | Current resource group |
| `LOCATION` | `[resourceGroup().location]` | Resource group location |
| `DEPLOYMENT_NAME` | `[deployment().name]` | Deployment name |
| `TENANT_ID` | `[subscription().tenantId]` | Tenant ID |

### Cross-Cloud Intrinsics Comparison

| Purpose | AWS (CF) | Azure (ARM) | GCP (CC) |
|---------|----------|-------------|----------|
| Reference resource | `Ref("Resource")` | `resourceId(...)` | `${resource.metadata.name}` |
| Get attribute | `GetAtt("R", "A")` | `reference(...).A` | N/A (use spec fields) |
| String substitute | `Sub("${A}-${B}")` | `format('{0}-{1}', A, B)` | N/A |
| Conditional | `If("Cond", T, F)` | `if(cond, T, F)` | N/A |
| Join strings | `Join(",", list)` | `join(',', list)` | N/A |
| Current region | `AWS_REGION` | `LOCATION` | `spec.location` |

---

## Dependency Handling

### How `dependsOn` Works in ARM

ARM templates use explicit `dependsOn` arrays:

```json
{
  "type": "Microsoft.Compute/virtualMachines",
  "name": "myVM",
  "dependsOn": [
    "[resourceId('Microsoft.Network/networkInterfaces', 'myNIC')]",
    "[resourceId('Microsoft.Storage/storageAccounts', 'myStorage')]"
  ]
}
```

### Automatic Dependency Detection

wetwire-azure computes `dependsOn` from `ref()` usage:

```
@wetwire_azure
class MyVM:
    resource: compute.VirtualMachine
    networkInterfaceRef = ref(MyNIC)      # → dependsOn: myNIC
    diagnosticsStorageRef = ref(MyStorage) # → dependsOn: myStorage
```

**Generated ARM JSON:**
```json
{
  "type": "Microsoft.Compute/virtualMachines",
  "name": "MyVM",
  "dependsOn": [
    "[resourceId('Microsoft.Network/networkInterfaces', 'MyNIC')]",
    "[resourceId('Microsoft.Storage/storageAccounts', 'MyStorage')]"
  ],
  "properties": {
    "networkProfile": {
      "networkInterfaces": [{
        "id": "[resourceId('Microsoft.Network/networkInterfaces', 'MyNIC')]"
      }]
    }
  }
}
```

### Cross-Cloud Dependency Comparison

| Aspect | AWS (CF) | Azure (ARM) | GCP (CC) |
|--------|----------|-------------|----------|
| Mechanism | `DependsOn` | `dependsOn` | `dependsOn` annotation |
| Detection | From `Ref`/`GetAtt` | From `resourceId`/`reference` | From `resourceRef` |
| Explicit | Optional | Optional | Optional |
| Implicit | Yes (intrinsics) | Yes (functions) | Yes (resourceRef) |

---

## Context Parameters

### CloudFormation Approach

```
from cloudformation_dataclasses.intrinsics import AWS_REGION, AWS_ACCOUNT_ID
region = AWS_REGION  # Resolved by AWS at deploy time
```

### Azure Approach: Explicit Context + ARM Functions

Azure uses ARM template functions for context:

```
from wetwire.azure import AzureContext, SUBSCRIPTION_ID, RESOURCE_GROUP, LOCATION

@dataclass
class AzureContext:
    subscription_id: str
    resource_group: str
    location: str = "eastus"

# Usage in resources
@wetwire_azure
class MyStorageAccount:
    resource: storage.StorageAccount
    location = LOCATION  # → "[resourceGroup().location]" in ARM
    # Or explicit: location = "eastus"

# Build
context = AzureContext(
    subscription_id="xxx-xxx-xxx",
    resource_group="myResourceGroup",
    location="eastus"
)
template = Template.from_registry(context=context)
print(template.to_json())
```

---

## User Workflow

wetwire-azure generates ARM JSON. The user handles diff and deploy with `az` CLI:

```bash
# 1. Generate ARM JSON (wetwire-azure)
python -m my_stack > template.json

# 2. Preview changes (az CLI - external, NATIVE what-if!)
az deployment group what-if \
  --resource-group myResourceGroup \
  --template-file template.json

# 3. Deploy (az CLI - external)
az deployment group create \
  --resource-group myResourceGroup \
  --template-file template.json

# 4. View resources (az CLI - external)
az resource list --resource-group myResourceGroup
```

### The what-if Operation: Native Diff

Azure's `what-if` is a **native feature** that shows:
- Resources to be created
- Resources to be modified (with property-level diff)
- Resources to be deleted
- No changes

```bash
$ az deployment group what-if --template-file template.json

Resource changes: 2 to create, 1 to modify, 0 to delete.

  + Microsoft.Network/virtualNetworks/myVNet
  + Microsoft.Network/networkInterfaces/myNIC
  ~ Microsoft.Compute/virtualMachines/myVM
    - properties.hardwareProfile.vmSize: "Standard_B1s"
    + properties.hardwareProfile.vmSize: "Standard_B2s"
```

**This is equivalent to CloudFormation Change Sets** - and a major advantage over GCP.

---

## Known Limitations

### In Scope (wetwire-azure can address)

| Limitation | Mitigation |
|------------|------------|
| **Dependency ordering** | Generate `dependsOn` arrays from `ref()` analysis |
| **Reference validation** | Validate `ref()` targets exist at build time |
| **Schema coverage gaps** | Track schema versions, document gaps |

### Out of Scope (Azure / az CLI issues)

| Limitation | Notes |
|------------|-------|
| **what-if limitations** | [Some properties show false changes](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/deploy-what-if#known-issues). Improving over time. |
| **Deployment scope** | Resource group, subscription, management group, tenant. User chooses. |
| **State management** | Azure Resource Manager handles this natively. |

**Philosophy:** wetwire-azure generates valid ARM JSON. What happens after `az deployment` is Azure's responsibility.

---

## Azure IaC Landscape (2025)

### Current State

| Tool | Status | Microsoft's Position |
|------|--------|---------------------|
| **ARM Templates** | Foundation | Supported, not deprecated |
| **Bicep** | **Recommended** | Microsoft's preferred IaC |
| **Azure Service Operator** | Growing | Kubernetes-native option |
| **Terraform** | Popular | Supported via AzureRM provider |

### Microsoft's Strategic Direction

Microsoft recommends **Bicep** for new Azure IaC:
- Bicep is a DSL that compiles to ARM JSON
- Cleaner syntax than raw ARM JSON
- Full feature parity with ARM templates
- Integrated into Azure CLI and VS Code

**The ARM JSON format is stable** - it's the foundation for Bicep, and will continue to be supported.

### What This Means for wetwire-azure

**The substrate is solid:**
- ARM JSON is not going away (Bicep compiles to it)
- Azure REST API specs are the source of truth
- `what-if` provides native diff capability
- Azure CLI is the standard deployment tool

---

## Alternative Output Formats

| Format | Method | Use Case |
|--------|--------|----------|
| **ARM JSON** (primary) | `template.to_json()` | Standard Azure deployments |
| ASO YAML | `template.to_aso_yaml()` | Kubernetes-native workflows |
| Bicep | `template.to_bicep()` | Human-readable (future) |

**Priority:** ARM JSON is primary. ASO YAML for K8s-native users. Bicep is future consideration.

```
template = Template.from_registry(context=context)

# Primary output
print(template.to_json())      # ARM JSON

# Alternative outputs
print(template.to_aso_yaml())  # Azure Service Operator CRDs
print(template.to_bicep())     # Bicep syntax (future)
```

### Azure Service Operator (ASO)

[Azure Service Operator](https://github.com/Azure/azure-service-operator) allows managing Azure resources via Kubernetes CRDs:
- **150+ Azure resources** supported
- **Generated from Azure OpenAPI specs**
- **Continuous reconciliation** (like GCP Config Connector)

**ASO vs ARM Path:**

| Aspect | ARM JSON Path | ASO Path |
|--------|---------------|----------|
| Output | ARM JSON | ASO CRD YAML |
| Deploy tool | `az deployment` | `kubectl apply` |
| Diff tool | `what-if` (native) | `kubectl diff` |
| State | Azure Resource Manager | Kubernetes API |
| Requires | Azure CLI | Kubernetes cluster |
| Reconciliation | Manual re-deploy | Continuous |

**Recommendation:** ARM JSON is primary because:
1. Native Azure tooling (no Kubernetes dependency)
2. Native what-if (superior to `kubectl diff`)
3. More analogous to cloudformation_dataclasses
4. Simpler for users who don't have Kubernetes

---

## Proposed Package Structure

```
wetwire-azure/
├── specs/
│   └── azure-resource-manager-schemas/  # Git submodule
│       └── schemas/                     # JSON schema files
├── src/wetwire_azure/
│   ├── core/
│   │   ├── base.py                      # AzureResource base class
│   │   ├── template.py                  # Template.from_registry()
│   │   ├── context.py                   # AzureContext, LOCATION, etc.
│   │   └── intrinsics.py                # ref(), resourceId(), reference()
│   ├── codegen/
│   │   ├── schema_parser.py             # Parse ARM JSON schemas
│   │   └── generator.py                 # Generate Python dataclasses
│   └── resources/                       # GENERATED (committed to git)
│       ├── compute/
│       │   ├── __init__.py
│       │   ├── virtualmachine.py
│       │   ├── virtualmachinescaleset.py
│       │   └── ...
│       ├── network/
│       ├── storage/
│       ├── web/
│       └── ... (organized by resource provider)
├── scripts/
│   ├── regenerate.sh                    # Parse schemas, generate code
│   └── update_schemas.sh                # git submodule update
└── pyproject.toml
```

---

## Implementation Path

### Phase 1: Schema Parser + Proof of Concept

- Clone [azure-resource-manager-schemas](https://github.com/Azure/azure-resource-manager-schemas) as git submodule
- Parse JSON schema files for resource definitions
- Extract property types, enums, required fields
- Generate Python dataclasses for `compute.VirtualMachine` and `storage.StorageAccount`
- Verify synthesis: Python → ARM JSON (valid structure)

### Phase 2: Core Library

- Implement `@wetwire_azure` decorator
- Implement `ref()` helper → generates `resourceId()` in output
- Implement `AzureContext` for subscription/resource group/location
- Implement `Template.from_registry()` → synthesizes ARM JSON
- Generate `.pyi` stubs for IDE support

### Phase 3: Production Ready

- Generate all Azure resource types from schemas
- Compute `dependsOn` arrays from `ref()` analysis
- Validate `ref()` targets at build time
- CLI tooling (`wetwire init --domain azure`, `wetwire lint`, `wetwire stubs`)
- Documentation and examples

### Optional: ASO Output

For Kubernetes-native users:
- `template.to_aso_yaml()` - Azure Service Operator CRDs
- Lower priority since ARM JSON is the primary focus

---

## Viability Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| Schema source | **Excellent** | azure-resource-manager-schemas in GitHub |
| Resource coverage | **Excellent** | ~1200 Azure resource types |
| Reference pattern | **Good** | `resourceId()` / `reference()` mapping |
| Dependency handling | **Good** | `dependsOn` generated from `ref()` |
| Diff capability | **Excellent** | Native `what-if` (like CF Change Sets!) |
| State management | **Excellent** | Azure Resource Manager handles this |
| Deploy tooling | **Excellent** | Native `az deployment` CLI |
| No external deps | **Yes** | Just Azure CLI |

### Value Proposition

**wetwire-azure adds value as a synthesis library by:**
1. **Type-safe Python authoring** - IDE autocomplete, `.pyi` stubs
2. **Build-time validation** - Catch `ref()` errors before deployment
3. **Cleaner API** - Python dataclasses vs raw ARM JSON
4. **Automatic dependsOn** - Computed from `ref()` analysis
5. **Familiar experience** - Same patterns as wetwire-aws

**What it does NOT do:**
- Deploy resources (use `az deployment group create`)
- Diff changes (use `az deployment group what-if`)
- Manage state (Azure Resource Manager handles this)

---

## Cross-Cloud Comparison

| Aspect | wetwire-aws | wetwire-gcp | wetwire-azure |
|--------|---------------------------|-----------------|-------------------|
| **Output format** | CloudFormation JSON | Config Connector YAML | ARM JSON |
| **Schema source** | CF Spec + botocore | Config Connector CRDs | ARM schemas |
| **Enum source** | botocore (separate) | CRD schemas (same) | ARM schemas (same) |
| **Deploy tool** | `aws cloudformation` | `kubectl apply` | `az deployment` |
| **Diff tool** | Change Sets (native) | `kubectl diff` | `what-if` (native) |
| **Diff quality** | Excellent | Adequate | Excellent |
| **Bootstrap requirement** | None | K8s cluster | None |
| **Deletion ordering** | Automatic (from Ref) | Manual (needs annotations) | Automatic (from resourceId) |
| **State** | CloudFormation | Kubernetes API | Azure RM |
| **External deps** | AWS CLI | kubectl + cluster | Azure CLI |
| **Reconciliation** | Manual | Continuous | Manual |
| **Resource count** | ~800 types | 452 CRDs | ~1200 types |

### Key Insights

**Azure has a better story than GCP** because:
- `what-if` is a native Azure feature (like CF Change Sets)
- GCP relies on `kubectl diff` which is less informative
- No Kubernetes infrastructure required

**Azure parallels CloudFormation closely:**
- Both have native diff preview
- Both have native CLIs
- Both use manual deployment model

---

## Conclusion

**Recommendation: Proceed with ARM JSON path.**

wetwire-azure as a **synthesis library** is highly viable:

| Factor | Assessment |
|--------|------------|
| **Schema source** | Excellent - azure-resource-manager-schemas in GitHub |
| **Output format** | ARM JSON - native Azure, Bicep-compatible |
| **Diff capability** | Excellent - native `what-if` (like CF Change Sets!) |
| **Deploy tooling** | Excellent - native `az deployment` CLI |
| **Scope clarity** | Synthesis only, like wetwire-aws |

**The Azure path is actually easier than GCP** because:
1. Native what-if (no need to rely on `kubectl diff`)
2. No Kubernetes dependency
3. Direct parallel to wetwire-aws
4. ARM JSON is stable and well-documented

**Accepted trade-offs:**
- ARM JSON is verbose (but we're generating it, not writing it)
- Some what-if edge cases (out of scope, Azure's responsibility)

**Next step:** Build Phase 1 proof of concept - parse ARM schemas, generate dataclasses for `VirtualMachine` and `StorageAccount`, synthesize valid ARM JSON.

---

**Part of the Wetwire Framework** — See DRAFT_DECLARATIVE_DATACLASS_FRAMEWORK.md for the universal pattern.

---

## Sources

### Primary (ARM Schemas)
- [azure-resource-manager-schemas](https://github.com/Azure/azure-resource-manager-schemas) - ARM JSON schema source
- [azure-rest-api-specs](https://github.com/Azure/azure-rest-api-specs) - Upstream API specifications
- [bicep-types-az](https://github.com/Azure/bicep-types-az) - Bicep type definitions (alternative source)
- [ARM Template Reference](https://learn.microsoft.com/en-us/azure/templates/) - Official documentation

### Azure Deployment
- [ARM Template Overview](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/overview) - How ARM templates work
- [Bicep Overview](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview) - Microsoft's recommended IaC
- [What-If Operation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-what-if) - Native diff/preview
- [Deploy with Azure CLI](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-cli) - Deployment commands

### Alternative Path (ASO)
- [Azure Service Operator](https://github.com/Azure/azure-service-operator) - Kubernetes-native option
- [ASO Supported Resources](https://azure.github.io/azure-service-operator/reference/) - 150+ Azure resources
- [ASO Documentation](https://azure.github.io/azure-service-operator/) - How ASO works
