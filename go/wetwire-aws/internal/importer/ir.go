// Package importer provides CloudFormation template import functionality.
// It parses CloudFormation YAML/JSON templates and generates Go code
// using wetwire-aws patterns.
package importer

// IntrinsicType represents a CloudFormation intrinsic function type.
type IntrinsicType int

const (
	IntrinsicRef IntrinsicType = iota
	IntrinsicGetAtt
	IntrinsicSub
	IntrinsicJoin
	IntrinsicSelect
	IntrinsicGetAZs
	IntrinsicIf
	IntrinsicEquals
	IntrinsicAnd
	IntrinsicOr
	IntrinsicNot
	IntrinsicCondition
	IntrinsicFindInMap
	IntrinsicBase64
	IntrinsicCidr
	IntrinsicImportValue
	IntrinsicSplit
	IntrinsicTransform
	IntrinsicValueOf
)

// String returns the CloudFormation name for this intrinsic type.
func (t IntrinsicType) String() string {
	switch t {
	case IntrinsicRef:
		return "Ref"
	case IntrinsicGetAtt:
		return "GetAtt"
	case IntrinsicSub:
		return "Sub"
	case IntrinsicJoin:
		return "Join"
	case IntrinsicSelect:
		return "Select"
	case IntrinsicGetAZs:
		return "GetAZs"
	case IntrinsicIf:
		return "If"
	case IntrinsicEquals:
		return "Equals"
	case IntrinsicAnd:
		return "And"
	case IntrinsicOr:
		return "Or"
	case IntrinsicNot:
		return "Not"
	case IntrinsicCondition:
		return "Condition"
	case IntrinsicFindInMap:
		return "FindInMap"
	case IntrinsicBase64:
		return "Base64"
	case IntrinsicCidr:
		return "Cidr"
	case IntrinsicImportValue:
		return "ImportValue"
	case IntrinsicSplit:
		return "Split"
	case IntrinsicTransform:
		return "Transform"
	case IntrinsicValueOf:
		return "ValueOf"
	default:
		return "Unknown"
	}
}

// IRIntrinsic represents a parsed CloudFormation intrinsic function.
// The Args structure varies by intrinsic type:
//   - Ref: string (logical_id)
//   - GetAtt: []string{logical_id, attribute}
//   - Sub: string or []any{template, variables_map}
//   - Join: []any{delimiter, values_list}
//   - Select: []any{index, list}
//   - If: []any{condition_name, true_value, false_value}
//   - Equals: []any{value1, value2}
//   - And/Or: []any (list of conditions)
//   - Not: any (single condition)
//   - FindInMap: []any{map_name, top_key, second_key}
//   - Base64: any (value to encode)
//   - Cidr: []any{ip_block, count, cidr_bits}
//   - ImportValue: any (export name)
//   - Split: []any{delimiter, source}
//   - GetAZs: string (region, empty for current)
type IRIntrinsic struct {
	Type IntrinsicType
	Args any
}

// IRProperty represents a resource property key-value pair.
type IRProperty struct {
	DomainName string // Original CloudFormation name (e.g., "BucketName")
	GoName     string // Go field name (e.g., "BucketName")
	Value      any    // Parsed value (may contain IRIntrinsic)
}

// IRParameter represents a CloudFormation parameter.
type IRParameter struct {
	LogicalID             string
	Type                  string
	Description           string
	Default               any
	AllowedValues         []any
	AllowedPattern        string
	MinLength             *int
	MaxLength             *int
	MinValue              *float64
	MaxValue              *float64
	ConstraintDescription string
	NoEcho                bool
}

// IRResource represents a CloudFormation resource.
type IRResource struct {
	LogicalID           string
	ResourceType        string // e.g., "AWS::S3::Bucket"
	Properties          map[string]*IRProperty
	DependsOn           []string
	Condition           string
	DeletionPolicy      string
	UpdateReplacePolicy string
	Metadata            map[string]any
}

// Service returns the AWS service name (e.g., "S3" from "AWS::S3::Bucket").
func (r *IRResource) Service() string {
	parts := splitResourceType(r.ResourceType)
	if len(parts) >= 2 {
		return parts[1]
	}
	return ""
}

// TypeName returns the resource type name (e.g., "Bucket" from "AWS::S3::Bucket").
func (r *IRResource) TypeName() string {
	parts := splitResourceType(r.ResourceType)
	if len(parts) >= 3 {
		return parts[2]
	}
	return ""
}

func splitResourceType(rt string) []string {
	var parts []string
	start := 0
	for i := 0; i < len(rt); i++ {
		if rt[i] == ':' && i+1 < len(rt) && rt[i+1] == ':' {
			parts = append(parts, rt[start:i])
			start = i + 2
			i++
		}
	}
	if start < len(rt) {
		parts = append(parts, rt[start:])
	}
	return parts
}

// IROutput represents a CloudFormation output.
type IROutput struct {
	LogicalID   string
	Value       any
	Description string
	ExportName  any // May be string or IRIntrinsic
	Condition   string
}

// IRMapping represents a CloudFormation mapping table.
type IRMapping struct {
	LogicalID string
	MapData   map[string]map[string]any
}

// IRCondition represents a CloudFormation condition.
type IRCondition struct {
	LogicalID  string
	Expression any // Usually an IRIntrinsic
}

// IRTemplate represents a complete parsed CloudFormation template.
type IRTemplate struct {
	Description              string
	AWSTemplateFormatVersion string
	Parameters               map[string]*IRParameter
	Mappings                 map[string]*IRMapping
	Conditions               map[string]*IRCondition
	Resources                map[string]*IRResource
	Outputs                  map[string]*IROutput
	SourceFile               string
	ReferenceGraph           map[string][]string // resource -> list of resources it references
}

// NewIRTemplate creates a new empty IR template.
func NewIRTemplate() *IRTemplate {
	return &IRTemplate{
		AWSTemplateFormatVersion: "2010-09-09",
		Parameters:               make(map[string]*IRParameter),
		Mappings:                 make(map[string]*IRMapping),
		Conditions:               make(map[string]*IRCondition),
		Resources:                make(map[string]*IRResource),
		Outputs:                  make(map[string]*IROutput),
		ReferenceGraph:           make(map[string][]string),
	}
}
