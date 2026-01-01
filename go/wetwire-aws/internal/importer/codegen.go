package importer

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
	"unicode"
)

// pseudoParameterConstants maps pseudo-parameter strings that appear as literal values
// to their Go constant equivalents. This handles edge cases where pseudo-parameters
// appear outside of Ref context.
var pseudoParameterConstants = map[string]string{
	"AWS::NoValue":          "AWS_NO_VALUE",
	"AWS::Region":           "AWS_REGION",
	"AWS::AccountId":        "AWS_ACCOUNT_ID",
	"AWS::StackName":        "AWS_STACK_NAME",
	"AWS::StackId":          "AWS_STACK_ID",
	"AWS::Partition":        "AWS_PARTITION",
	"AWS::URLSuffix":        "AWS_URL_SUFFIX",
	"AWS::NotificationARNs": "AWS_NOTIFICATION_ARNS",
}

// GenerateCode generates Go code from a parsed IR template.
// Returns a map of filename to content.
func GenerateCode(template *IRTemplate, packageName string) map[string]string {
	ctx := newCodegenContext(template, packageName)

	// Generate single file output
	code := generateSingleFile(ctx)

	return map[string]string{
		packageName + ".go": code,
	}
}

// codegenContext holds state during code generation.
type codegenContext struct {
	template         *IRTemplate
	packageName      string
	imports          map[string]bool // import path -> true
	resourceOrder    []string        // topologically sorted resource IDs
	currentResource  string          // current resource module being generated (e.g., "ec2", "cloudfront")
	currentTypeName  string          // current resource type name (e.g., "Distribution", "VPC")
	currentProperty  string          // current property being generated (e.g., "SecurityGroupIngress")
	currentLogicalID string          // current resource's logical ID (e.g., "SecurityGroup")

	// Block-style property type declarations
	// Each property type instance becomes its own var declaration
	propertyBlocks []propertyBlock // collected during resource traversal
	blockNameCount map[string]int  // for generating unique names

	// Track which parameters are directly referenced via Ref
	usedParameters map[string]bool
}

// propertyBlock represents a top-level var declaration for a property type instance.
type propertyBlock struct {
	varName    string         // e.g., "SecurityGroupHttpsIngress"
	typeName   string         // e.g., "ec2.SecurityGroup_Ingress"
	properties map[string]any // the property values
}

// knownPropertyTypes maps (service, propertyName) to the typed struct to use.
// Property types are qualified with their parent resource (e.g., SecurityGroup_Ingress).
// This enables generating []ec2.SecurityGroup_Ingress{...} instead of []any{map[string]any{...}}.
// NOTE: Only include types where the parent resource name matches the actual generated type.
// Many property types are shared across resources (e.g., EC2Fleet_BlockDeviceMapping is used by Instance).
var knownPropertyTypes = map[string]map[string]string{
	"ec2": {
		"SecurityGroupIngress": "SecurityGroup_Ingress",
		"SecurityGroupEgress":  "SecurityGroup_Egress",
		// BlockDeviceMappings and Volumes removed - types are shared across resources
	},
	// iam Policies removed - Role_Policy may not exist
	// elasticloadbalancingv2 types removed - may not match actual generated types
}

func newCodegenContext(template *IRTemplate, packageName string) *codegenContext {
	ctx := &codegenContext{
		template:       template,
		packageName:    packageName,
		imports:        make(map[string]bool),
		blockNameCount: make(map[string]int),
		usedParameters: make(map[string]bool),
	}

	// Topologically sort resources
	ctx.resourceOrder = topologicalSort(template)

	return ctx
}

func generateSingleFile(ctx *codegenContext) string {
	var sections []string

	// Build code sections (to determine needed imports)
	var codeSections []string

	// First pass: generate resources, conditions, and outputs to track parameter usage
	// Resources (in dependency order)
	var resourceSections []string
	for _, resourceID := range ctx.resourceOrder {
		resource := ctx.template.Resources[resourceID]
		resourceSections = append(resourceSections, generateResource(ctx, resource))
	}

	// Conditions (may reference parameters)
	var conditionSections []string
	for _, logicalID := range sortedKeys(ctx.template.Conditions) {
		condition := ctx.template.Conditions[logicalID]
		conditionSections = append(conditionSections, generateCondition(ctx, condition))
	}

	// Outputs (may reference parameters)
	var outputSections []string
	for _, logicalID := range sortedKeys(ctx.template.Outputs) {
		output := ctx.template.Outputs[logicalID]
		outputSections = append(outputSections, generateOutput(ctx, output))
	}

	// Generate parameters - only those directly referenced via Ref
	// Uses Param("name") for clarity that it's a parameter
	for _, logicalID := range sortedKeys(ctx.template.Parameters) {
		if !ctx.usedParameters[logicalID] {
			continue // Skip unused parameters
		}
		param := ctx.template.Parameters[logicalID]
		codeSections = append(codeSections, generateParameter(ctx, param))
	}

	// Mappings
	for _, logicalID := range sortedKeys(ctx.template.Mappings) {
		mapping := ctx.template.Mappings[logicalID]
		codeSections = append(codeSections, generateMapping(ctx, mapping))
	}

	// Add conditions, resources, outputs in proper order
	codeSections = append(codeSections, conditionSections...)
	codeSections = append(codeSections, resourceSections...)
	codeSections = append(codeSections, outputSections...)

	// Package header
	header := fmt.Sprintf("// Package %s contains CloudFormation resources.\n", ctx.packageName)
	if ctx.template.Description != "" {
		header += fmt.Sprintf("// %s\n", ctx.template.Description)
	}
	header += "//\n// Generated by wetwire-aws import.\n"
	header += fmt.Sprintf("package %s\n", ctx.packageName)
	sections = append(sections, header)

	// Imports - use dot import for intrinsics for cleaner syntax
	if len(ctx.imports) > 0 {
		var importLines []string
		sortedImports := sortedKeys(ctx.imports)
		for _, imp := range sortedImports {
			if imp == "github.com/lex00/wetwire-aws/intrinsics" {
				importLines = append(importLines, fmt.Sprintf("\t. %q", imp))
			} else {
				importLines = append(importLines, fmt.Sprintf("\t%q", imp))
			}
		}
		sections = append(sections, fmt.Sprintf("import (\n%s\n)", strings.Join(importLines, "\n")))
	}

	// Code sections
	sections = append(sections, codeSections...)

	return strings.Join(sections, "\n\n") + "\n"
}

func generateParameter(ctx *codegenContext, param *IRParameter) string {
	var lines []string

	varName := param.LogicalID
	if param.Description != "" {
		lines = append(lines, fmt.Sprintf("// %s - %s", varName, param.Description))
	}

	// Use Param() helper for clarity that this is a parameter reference
	ctx.imports["github.com/lex00/wetwire-aws/intrinsics"] = true
	lines = append(lines, fmt.Sprintf("var %s = Param(%q)", varName, param.LogicalID))

	return strings.Join(lines, "\n")
}

func generateMapping(ctx *codegenContext, mapping *IRMapping) string {
	varName := mapping.LogicalID + "Mapping"
	value := valueToGo(ctx, mapping.MapData, 0)
	return fmt.Sprintf("var %s = %s", varName, value)
}

func generateCondition(ctx *codegenContext, condition *IRCondition) string {
	varName := condition.LogicalID + "Condition"
	value := valueToGo(ctx, condition.Expression, 0)
	return fmt.Sprintf("var %s = %s", varName, value)
}

func generateResource(ctx *codegenContext, resource *IRResource) string {
	var lines []string

	// Resolve resource type to Go module and type
	module, typeName := resolveResourceType(resource.ResourceType)
	if module == "" {
		lines = append(lines, fmt.Sprintf("// Unknown resource type: %s", resource.ResourceType))
		module = "unknown"
		typeName = "Resource"
	}

	// Add import
	ctx.imports[fmt.Sprintf("github.com/lex00/wetwire-aws/resources/%s", module)] = true

	// Set current resource context for typed property generation
	ctx.currentResource = module
	ctx.currentTypeName = typeName
	ctx.currentLogicalID = resource.LogicalID

	// Clear property blocks for this resource
	ctx.propertyBlocks = nil

	// First pass: collect property blocks by traversing properties
	// This populates ctx.propertyBlocks with any nested property type instances
	resourceProps := make(map[string]string) // propName -> generated value
	for _, propName := range sortedKeys(resource.Properties) {
		prop := resource.Properties[propName]
		ctx.currentProperty = propName
		var value string
		if propName == "Tags" {
			value = tagsToBlockStyle(ctx, prop.Value)
		} else if typedStruct := getTypedPropertyStruct(ctx.currentResource, propName); typedStruct != "" {
			// Block style: extract items as separate var declarations
			value = typedArrayToBlockStyle(ctx, prop.Value, typedStruct)
		} else {
			// Pass property name for typed struct generation
			value = valueToGoWithProperty(ctx, prop.Value, 1, propName)
		}
		resourceProps[prop.GoName] = value
	}

	// Generate property blocks BEFORE the resource
	for _, block := range ctx.propertyBlocks {
		lines = append(lines, generatePropertyBlock(ctx, block))
		lines = append(lines, "") // blank line between blocks
	}

	varName := resource.LogicalID

	// Build struct literal for the resource
	lines = append(lines, fmt.Sprintf("var %s = %s.%s{", varName, module, typeName))

	// Properties (in sorted order)
	for _, propName := range sortedKeys(resource.Properties) {
		prop := resource.Properties[propName]
		value := resourceProps[prop.GoName]
		lines = append(lines, fmt.Sprintf("\t%s: %s,", prop.GoName, value))
	}

	lines = append(lines, "}")

	return strings.Join(lines, "\n")
}

// generatePropertyBlock generates a var declaration for a property type block.
func generatePropertyBlock(ctx *codegenContext, block propertyBlock) string {
	var lines []string
	lines = append(lines, fmt.Sprintf("var %s = %s{", block.varName, block.typeName))

	// Sort property keys for deterministic output
	keys := make([]string, 0, len(block.properties))
	for k := range block.properties {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	for _, k := range keys {
		v := block.properties[k]
		fieldVal := valueToGo(ctx, v, 0)
		lines = append(lines, fmt.Sprintf("\t%s: %s,", k, fieldVal))
	}

	lines = append(lines, "}")
	return strings.Join(lines, "\n")
}

// getTypedPropertyStruct returns the struct type name for a known property array.
func getTypedPropertyStruct(service, propName string) string {
	if serviceProps, ok := knownPropertyTypes[service]; ok {
		if structName, ok := serviceProps[propName]; ok {
			return structName
		}
	}
	return ""
}

// typedArrayToBlockStyle converts an array to block-style: each item becomes a separate
// var declaration, and returns a slice of references to those vars.
// Example output: []ec2.SecurityGroup_Ingress{SecurityGroupHttpsIngress, SecurityGroupHttpIngress}
func typedArrayToBlockStyle(ctx *codegenContext, value any, structType string) string {
	arr, ok := value.([]any)
	if !ok || len(arr) == 0 {
		return fmt.Sprintf("[]%s.%s{}", ctx.currentResource, structType)
	}

	var varNames []string
	for _, item := range arr {
		itemMap, ok := item.(map[string]any)
		if !ok {
			// Fallback: can't extract as block, skip
			continue
		}

		// Generate a unique var name based on resource + property + distinguishing value
		varName := generateBlockVarName(ctx, itemMap)
		fullTypeName := fmt.Sprintf("%s.%s", ctx.currentResource, structType)

		// Add to property blocks
		ctx.propertyBlocks = append(ctx.propertyBlocks, propertyBlock{
			varName:    varName,
			typeName:   fullTypeName,
			properties: itemMap,
		})

		varNames = append(varNames, varName)
	}

	if len(varNames) == 0 {
		return fmt.Sprintf("[]%s.%s{}", ctx.currentResource, structType)
	}

	// Return slice of var references
	return fmt.Sprintf("[]%s.%s{%s}", ctx.currentResource, structType, strings.Join(varNames, ", "))
}

// generateBlockVarName generates a unique, descriptive var name for a property block.
// Uses the resource logical ID + property name + a distinguishing value from the block.
func generateBlockVarName(ctx *codegenContext, props map[string]any) string {
	// Try to find a distinguishing value in the properties
	// Priority: Port numbers, CidrIp, Name fields, etc.
	var suffix string

	// For security group ingress/egress, use port info
	if fromPort, ok := props["FromPort"]; ok {
		if toPort, ok := props["ToPort"]; ok {
			if fromPort == toPort {
				suffix = fmt.Sprintf("Port%v", fromPort)
			} else {
				suffix = fmt.Sprintf("Ports%vTo%v", fromPort, toPort)
			}
		} else {
			suffix = fmt.Sprintf("Port%v", fromPort)
		}
		// Add protocol if not tcp
		if proto, ok := props["IpProtocol"].(string); ok && proto != "tcp" {
			suffix += strings.ToUpper(proto)
		}
	}

	// For other types, look for name-like fields
	if suffix == "" {
		for _, key := range []string{"Name", "Key", "Type", "DeviceName", "PolicyName"} {
			if val, ok := props[key]; ok {
				if s, ok := val.(string); ok && s != "" {
					// Clean up the value for use in a var name
					suffix = cleanForVarName(s)
					break
				}
			}
		}
	}

	// Fallback to index if no distinguishing value found
	if suffix == "" {
		baseKey := ctx.currentLogicalID + ctx.currentProperty
		ctx.blockNameCount[baseKey]++
		suffix = fmt.Sprintf("%d", ctx.blockNameCount[baseKey])
	}

	return ctx.currentLogicalID + suffix
}

// cleanForVarName cleans a string value for use in a Go variable name.
func cleanForVarName(s string) string {
	// Remove common prefixes and special chars, convert to PascalCase
	s = strings.ReplaceAll(s, "/", "")
	s = strings.ReplaceAll(s, "-", "")
	s = strings.ReplaceAll(s, "_", "")
	s = strings.ReplaceAll(s, ".", "")
	s = strings.ReplaceAll(s, ":", "")

	// Capitalize first letter
	if len(s) > 0 {
		s = strings.ToUpper(s[:1]) + s[1:]
	}

	// Limit length
	if len(s) > 20 {
		s = s[:20]
	}

	return s
}

// tagsToBlockStyle converts tags to block style with separate var declarations.
func tagsToBlockStyle(ctx *codegenContext, value any) string {
	ctx.imports["github.com/lex00/wetwire-aws/intrinsics"] = true

	tags, ok := value.([]any)
	if !ok || len(tags) == 0 {
		return "[]any{}"
	}

	var varNames []string
	for _, tag := range tags {
		tagMap, ok := tag.(map[string]any)
		if !ok {
			continue
		}

		key, hasKey := tagMap["Key"]
		val, hasValue := tagMap["Value"]
		if !hasKey || !hasValue {
			continue
		}

		// Generate var name from tag key
		keyStr, ok := key.(string)
		if !ok {
			continue
		}
		varName := ctx.currentLogicalID + "Tag" + cleanForVarName(keyStr)

		// Add to property blocks
		ctx.propertyBlocks = append(ctx.propertyBlocks, propertyBlock{
			varName:    varName,
			typeName:   "Tag",
			properties: map[string]any{"Key": key, "Value": val},
		})

		varNames = append(varNames, varName)
	}

	if len(varNames) == 0 {
		return "[]any{}"
	}

	return fmt.Sprintf("[]any{%s}", strings.Join(varNames, ", "))
}

func generateOutput(ctx *codegenContext, output *IROutput) string {
	var lines []string

	varName := output.LogicalID + "Output"

	if output.Description != "" {
		lines = append(lines, fmt.Sprintf("// %s - %s", varName, output.Description))
	}

	// Use the Output type from intrinsics
	ctx.imports["github.com/lex00/wetwire-aws/intrinsics"] = true
	lines = append(lines, fmt.Sprintf("var %s = Output{", varName))

	value := valueToGo(ctx, output.Value, 1)
	lines = append(lines, fmt.Sprintf("\tValue:       %s,", value))

	if output.Description != "" {
		lines = append(lines, fmt.Sprintf("\tDescription: %q,", output.Description))
	}
	if output.ExportName != nil {
		exportValue := valueToGo(ctx, output.ExportName, 1)
		lines = append(lines, fmt.Sprintf("\tExportName:  %s,", exportValue))
	}
	if output.Condition != "" {
		lines = append(lines, fmt.Sprintf("\tCondition:   %q,", output.Condition))
	}

	lines = append(lines, "}")

	return strings.Join(lines, "\n")
}

// valueToGo converts an IR value to Go source code.
func valueToGo(ctx *codegenContext, value any, indent int) string {
	return valueToGoWithProperty(ctx, value, indent, "")
}

// valueToGoWithProperty converts an IR value to Go source code, with property context.
// The propName parameter indicates the property name if this value is a field in a struct,
// which allows us to determine the typed struct name for nested property types.
func valueToGoWithProperty(ctx *codegenContext, value any, indent int, propName string) string {
	indentStr := strings.Repeat("\t", indent)
	nextIndent := strings.Repeat("\t", indent+1)

	if value == nil {
		return "nil"
	}

	switch v := value.(type) {
	case *IRIntrinsic:
		return intrinsicToGo(ctx, v)

	case bool:
		if v {
			return "true"
		}
		return "false"

	case int:
		return fmt.Sprintf("%d", v)

	case int64:
		return fmt.Sprintf("%d", v)

	case float64:
		// Check if it's a whole number
		if v == float64(int64(v)) {
			return fmt.Sprintf("%d", int64(v))
		}
		return fmt.Sprintf("%g", v)

	case string:
		// Check for pseudo-parameters that should be constants
		if pseudoConst, ok := pseudoParameterConstants[v]; ok {
			ctx.imports["github.com/lex00/wetwire-aws/intrinsics"] = true
			return pseudoConst
		}
		return fmt.Sprintf("%q", v)

	case []any:
		if len(v) == 0 {
			return "[]any{}"
		}
		// Check if this is an array of objects that should use typed slice
		if propName != "" && len(v) > 0 {
			if _, isMap := v[0].(map[string]any); isMap {
				// Determine the element type name (singular form for arrays)
				elemTypeName := getArrayElementTypeName(ctx, propName)
				if elemTypeName != "" {
					var items []string
					for _, item := range v {
						// Pass singular element type name for nested properties
						items = append(items, nextIndent+valueToGoWithProperty(ctx, item, indent+1, singularize(propName))+",")
					}
					return fmt.Sprintf("[]%s.%s{\n%s\n%s}", ctx.currentResource, elemTypeName, strings.Join(items, "\n"), indentStr)
				}
			}
		}
		var items []string
		for _, item := range v {
			items = append(items, nextIndent+valueToGoWithProperty(ctx, item, indent+1, "")+",")
		}
		return fmt.Sprintf("[]any{\n%s\n%s}", strings.Join(items, "\n"), indentStr)

	case map[string]any:
		if len(v) == 0 {
			return "map[string]any{}"
		}
		// Check if this is an intrinsic function map (single key starting with "Ref" or "Fn::")
		if len(v) == 1 {
			for k := range v {
				if k == "Ref" || strings.HasPrefix(k, "Fn::") || k == "Condition" {
					// Convert to IRIntrinsic and use intrinsicToGo
					intrinsic := mapToIntrinsic(v)
					if intrinsic != nil {
						return intrinsicToGo(ctx, intrinsic)
					}
				}
			}
		}

		// Try to use a typed struct based on property context
		// But only if all keys are valid Go identifiers
		typeName := getPropertyTypeName(ctx, propName)
		if typeName != "" && allKeysValidIdentifiers(v) {
			var items []string
			for _, k := range sortedKeys(v) {
				val := v[k]
				items = append(items, fmt.Sprintf("%s%s: %s,", nextIndent, k, valueToGoWithProperty(ctx, val, indent+1, k)))
			}
			return fmt.Sprintf("%s.%s{\n%s\n%s}", ctx.currentResource, typeName, strings.Join(items, "\n"), indentStr)
		}

		// Fallback to map[string]any
		var items []string
		for _, k := range sortedKeys(v) {
			val := v[k]
			items = append(items, fmt.Sprintf("%s%q: %s,", nextIndent, k, valueToGoWithProperty(ctx, val, indent+1, k)))
		}
		return fmt.Sprintf("map[string]any{\n%s\n%s}", strings.Join(items, "\n"), indentStr)
	}

	return fmt.Sprintf("%#v", value)
}

// getPropertyTypeName returns the typed struct name for a property, if known.
// CloudFormation property types are always flat: {ResourceType}_{PropertyTypeName}
// e.g., Distribution_DistributionConfig, Distribution_DefaultCacheBehavior, Distribution_Cookies
// Returns empty string if the property should use map[string]any.
func getPropertyTypeName(ctx *codegenContext, propName string) string {
	if propName == "" || ctx.currentTypeName == "" {
		return ""
	}

	// Skip known fields that should remain as map[string]any or are handled specially
	skipFields := map[string]bool{
		"Tags":     true,
		"Metadata": true,
	}
	if skipFields[propName] {
		return ""
	}

	// CloudFormation property types are flat: {ResourceType}_{PropertyTypeName}
	// The property type name is typically the same as the property field name
	return ctx.currentTypeName + "_" + propName
}

// getArrayElementTypeName returns the typed struct name for array elements.
// CloudFormation uses singular names for element types: Origins -> Origin
func getArrayElementTypeName(ctx *codegenContext, propName string) string {
	if propName == "" || ctx.currentTypeName == "" {
		return ""
	}

	// Skip known fields that should remain as []any
	skipFields := map[string]bool{
		"Tags": true,
	}
	if skipFields[propName] {
		return ""
	}

	// Array element types use singular form
	singular := singularize(propName)
	return ctx.currentTypeName + "_" + singular
}

// singularize converts a plural property name to singular for element types.
// e.g., Origins -> Origin, CacheBehaviors -> CacheBehavior
func singularize(name string) string {
	// Handle common CloudFormation patterns
	if strings.HasSuffix(name, "ies") {
		// e.g., Policies -> Policy
		return name[:len(name)-3] + "y"
	}
	if strings.HasSuffix(name, "sses") {
		// e.g., Addresses -> Address (but keep one 's')
		return name[:len(name)-2]
	}
	if strings.HasSuffix(name, "s") && !strings.HasSuffix(name, "ss") {
		// e.g., Origins -> Origin, but not Address -> Addres
		return name[:len(name)-1]
	}
	return name
}

// allKeysValidIdentifiers checks if all keys in a map are valid Go identifiers.
// Returns false if any key contains special characters like ':' or starts with a number.
func allKeysValidIdentifiers(m map[string]any) bool {
	for k := range m {
		if !isValidGoIdentifier(k) {
			return false
		}
	}
	return true
}

// isValidGoIdentifier checks if a string is a valid Go identifier.
func isValidGoIdentifier(s string) bool {
	if len(s) == 0 {
		return false
	}
	for i, r := range s {
		if i == 0 {
			if !unicode.IsLetter(r) && r != '_' {
				return false
			}
		} else {
			if !unicode.IsLetter(r) && !unicode.IsDigit(r) && r != '_' {
				return false
			}
		}
	}
	// Also check for Go keywords
	return !isGoKeyword(s)
}

// mapToIntrinsic converts a map with an intrinsic key to an IRIntrinsic.
// Returns nil if the map is not a recognized intrinsic.
func mapToIntrinsic(m map[string]any) *IRIntrinsic {
	if len(m) != 1 {
		return nil
	}

	for k, v := range m {
		var intrinsicType IntrinsicType
		switch k {
		case "Ref":
			intrinsicType = IntrinsicRef
		case "Fn::GetAtt":
			intrinsicType = IntrinsicGetAtt
		case "Fn::Sub":
			intrinsicType = IntrinsicSub
		case "Fn::Join":
			intrinsicType = IntrinsicJoin
		case "Fn::Select":
			intrinsicType = IntrinsicSelect
		case "Fn::GetAZs":
			intrinsicType = IntrinsicGetAZs
		case "Fn::If":
			intrinsicType = IntrinsicIf
		case "Fn::Equals":
			intrinsicType = IntrinsicEquals
		case "Fn::And":
			intrinsicType = IntrinsicAnd
		case "Fn::Or":
			intrinsicType = IntrinsicOr
		case "Fn::Not":
			intrinsicType = IntrinsicNot
		case "Fn::Base64":
			intrinsicType = IntrinsicBase64
		case "Fn::FindInMap":
			intrinsicType = IntrinsicFindInMap
		case "Fn::Cidr":
			intrinsicType = IntrinsicCidr
		case "Fn::ImportValue":
			intrinsicType = IntrinsicImportValue
		case "Fn::Split":
			intrinsicType = IntrinsicSplit
		case "Fn::Transform":
			intrinsicType = IntrinsicTransform
		case "Condition":
			intrinsicType = IntrinsicCondition
		default:
			return nil
		}
		return &IRIntrinsic{Type: intrinsicType, Args: v}
	}
	return nil
}

// intrinsicToGo converts an IRIntrinsic to Go source code.
// Uses function call syntax for cleaner generated code:
//
//	Sub("template") instead of intrinsics.Sub{String: "template"}
//	Select(0, GetAZs()) instead of intrinsics.Select{Index: 0, List: intrinsics.GetAZs{}}
func intrinsicToGo(ctx *codegenContext, intrinsic *IRIntrinsic) string {
	ctx.imports["github.com/lex00/wetwire-aws/intrinsics"] = true

	switch intrinsic.Type {
	case IntrinsicRef:
		target := fmt.Sprintf("%v", intrinsic.Args)
		// Check if it's a pseudo-parameter
		if strings.HasPrefix(target, "AWS::") {
			return pseudoParameterToGo(ctx, target)
		}
		// Check if it's a known resource - use bare name (no-parens pattern)
		if _, ok := ctx.template.Resources[target]; ok {
			return target
		}
		// Check if it's a parameter - use bare name and track usage
		if _, ok := ctx.template.Parameters[target]; ok {
			ctx.usedParameters[target] = true
			return target
		}
		// Unknown reference - use inline Ref
		return fmt.Sprintf("Ref{%q}", target)

	case IntrinsicGetAtt:
		var logicalID, attr string
		switch args := intrinsic.Args.(type) {
		case []string:
			if len(args) >= 2 {
				logicalID = args[0]
				attr = args[1]
			}
		case []any:
			if len(args) >= 2 {
				logicalID = fmt.Sprintf("%v", args[0])
				attr = fmt.Sprintf("%v", args[1])
			}
		}
		// Check if it's a known resource - use attribute access
		if _, ok := ctx.template.Resources[logicalID]; ok {
			return fmt.Sprintf("%s.%s", logicalID, attr)
		}
		return fmt.Sprintf("intrinsics.GetAtt(%q, %q)", logicalID, attr)

	case IntrinsicSub:
		switch args := intrinsic.Args.(type) {
		case string:
			return fmt.Sprintf("Sub{%q}", args)
		case []any:
			if len(args) >= 2 {
				template := fmt.Sprintf("%v", args[0])
				vars := valueToGo(ctx, args[1], 0)
				return fmt.Sprintf("SubWithMap{%q, %s}", template, vars)
			} else if len(args) == 1 {
				template := fmt.Sprintf("%v", args[0])
				return fmt.Sprintf("Sub{%q}", template)
			}
		}
		return `Sub{""}`

	case IntrinsicJoin:
		if args, ok := intrinsic.Args.([]any); ok && len(args) >= 2 {
			delimiter := valueToGo(ctx, args[0], 0)
			values := valueToGo(ctx, args[1], 0)
			return fmt.Sprintf("Join{%s, %s}", delimiter, values)
		}
		return `Join{"", nil}`

	case IntrinsicSelect:
		if args, ok := intrinsic.Args.([]any); ok && len(args) >= 2 {
			index := valueToGo(ctx, args[0], 0)
			list := valueToGo(ctx, args[1], 0)
			return fmt.Sprintf("Select{%s, %s}", index, list)
		}
		return "Select{0, nil}"

	case IntrinsicGetAZs:
		region := fmt.Sprintf("%v", intrinsic.Args)
		if region == "" || region == "<nil>" {
			return "GetAZs{}"
		}
		return fmt.Sprintf("GetAZs{%q}", region)

	case IntrinsicIf:
		if args, ok := intrinsic.Args.([]any); ok && len(args) >= 3 {
			condName := fmt.Sprintf("%v", args[0])
			trueVal := valueToGo(ctx, args[1], 0)
			falseVal := valueToGo(ctx, args[2], 0)
			return fmt.Sprintf("If{%q, %s, %s}", condName, trueVal, falseVal)
		}
		return `If{"", nil, nil}`

	case IntrinsicEquals:
		if args, ok := intrinsic.Args.([]any); ok && len(args) >= 2 {
			val1 := valueToGo(ctx, args[0], 0)
			val2 := valueToGo(ctx, args[1], 0)
			return fmt.Sprintf("Equals{%s, %s}", val1, val2)
		}
		return "Equals{nil, nil}"

	case IntrinsicAnd:
		if args, ok := intrinsic.Args.([]any); ok {
			values := valueToGo(ctx, args, 0)
			return fmt.Sprintf("And{%s}", values)
		}
		return "And{nil}"

	case IntrinsicOr:
		if args, ok := intrinsic.Args.([]any); ok {
			values := valueToGo(ctx, args, 0)
			return fmt.Sprintf("Or{%s}", values)
		}
		return "Or{nil}"

	case IntrinsicNot:
		condition := valueToGo(ctx, intrinsic.Args, 0)
		return fmt.Sprintf("Not{%s}", condition)

	case IntrinsicCondition:
		condName := fmt.Sprintf("%v", intrinsic.Args)
		return fmt.Sprintf("Condition{%q}", condName)

	case IntrinsicFindInMap:
		if args, ok := intrinsic.Args.([]any); ok && len(args) >= 3 {
			mapName := fmt.Sprintf("%v", args[0])
			topKey := valueToGo(ctx, args[1], 0)
			secondKey := valueToGo(ctx, args[2], 0)
			return fmt.Sprintf("FindInMap{%q, %s, %s}", mapName, topKey, secondKey)
		}
		return `FindInMap{"", nil, nil}`

	case IntrinsicBase64:
		value := valueToGo(ctx, intrinsic.Args, 0)
		return fmt.Sprintf("Base64{%s}", value)

	case IntrinsicCidr:
		if args, ok := intrinsic.Args.([]any); ok && len(args) >= 3 {
			ipBlock := valueToGo(ctx, args[0], 0)
			count := valueToGo(ctx, args[1], 0)
			cidrBits := valueToGo(ctx, args[2], 0)
			return fmt.Sprintf("Cidr{%s, %s, %s}", ipBlock, count, cidrBits)
		}
		return "Cidr{nil, nil, nil}"

	case IntrinsicImportValue:
		value := valueToGo(ctx, intrinsic.Args, 0)
		return fmt.Sprintf("ImportValue{%s}", value)

	case IntrinsicSplit:
		if args, ok := intrinsic.Args.([]any); ok && len(args) >= 2 {
			delimiter := valueToGo(ctx, args[0], 0)
			source := valueToGo(ctx, args[1], 0)
			return fmt.Sprintf("Split{%s, %s}", delimiter, source)
		}
		return `Split{"", nil}`

	case IntrinsicTransform:
		value := valueToGo(ctx, intrinsic.Args, 0)
		return fmt.Sprintf("Transform{%s}", value)
	}

	return fmt.Sprintf("/* unknown intrinsic: %s */nil", intrinsic.Type)
}

// pseudoParameterToGo converts an AWS pseudo-parameter to Go.
// Uses dot import, so no intrinsics. prefix needed.
func pseudoParameterToGo(ctx *codegenContext, name string) string {
	ctx.imports["github.com/lex00/wetwire-aws/intrinsics"] = true
	switch name {
	case "AWS::Region":
		return "AWS_REGION"
	case "AWS::AccountId":
		return "AWS_ACCOUNT_ID"
	case "AWS::StackName":
		return "AWS_STACK_NAME"
	case "AWS::StackId":
		return "AWS_STACK_ID"
	case "AWS::Partition":
		return "AWS_PARTITION"
	case "AWS::URLSuffix":
		return "AWS_URL_SUFFIX"
	case "AWS::NoValue":
		return "AWS_NO_VALUE"
	case "AWS::NotificationARNs":
		return "AWS_NOTIFICATION_ARNS"
	default:
		return fmt.Sprintf("Ref{%q}", name)
	}
}

// rewriteSubString rewrites ${Resource} patterns in Sub strings.
func rewriteSubString(ctx *codegenContext, template string) string {
	// For now, just quote the string
	// TODO: Implement proper rewriting for known resources
	return fmt.Sprintf("%q", template)
}

// resolveResourceType converts a CloudFormation resource type to Go module and type name.
// e.g., "AWS::S3::Bucket" -> ("s3", "Bucket")
func resolveResourceType(cfType string) (module, typeName string) {
	parts := strings.Split(cfType, "::")
	if len(parts) != 3 || parts[0] != "AWS" {
		return "", ""
	}

	service := parts[1]
	resource := parts[2]

	// Map service name to Go module name
	module = strings.ToLower(service)

	typeName = resource

	return module, typeName
}

// topologicalSort returns resources in dependency order (dependencies first).
func topologicalSort(template *IRTemplate) []string {
	// Build dependency graph: node -> list of nodes it depends on
	deps := make(map[string][]string)
	for id := range template.Resources {
		deps[id] = nil
	}
	for source, targets := range template.ReferenceGraph {
		if _, ok := template.Resources[source]; !ok {
			continue
		}
		for _, target := range targets {
			if _, ok := template.Resources[target]; ok {
				// source depends on target
				deps[source] = append(deps[source], target)
			}
		}
	}

	// Kahn's algorithm - compute in-degree (nodes that depend on this one)
	inDegree := make(map[string]int)
	for id := range template.Resources {
		inDegree[id] = 0
	}
	// For each dependency edge, increment the in-degree of the dependent
	for id, idDeps := range deps {
		inDegree[id] = len(idDeps)
	}

	// Start with nodes that have no dependencies (in-degree 0)
	var queue []string
	for id, degree := range inDegree {
		if degree == 0 {
			queue = append(queue, id)
		}
	}
	sort.Strings(queue) // Stable order

	var result []string
	processed := make(map[string]bool)

	for len(queue) > 0 {
		// Take from front
		node := queue[0]
		queue = queue[1:]

		if processed[node] {
			continue
		}
		processed[node] = true
		result = append(result, node)

		// Find nodes that depend on this node
		for id, idDeps := range deps {
			if processed[id] {
				continue
			}
			for _, dep := range idDeps {
				if dep == node {
					inDegree[id]--
					if inDegree[id] == 0 {
						queue = append(queue, id)
					}
					break
				}
			}
		}
		sort.Strings(queue)
	}

	// Handle cycles by adding remaining nodes
	for id := range template.Resources {
		if !processed[id] {
			result = append(result, id)
		}
	}

	return result
}

// sortedKeys returns sorted keys from a map.
func sortedKeys[V any](m map[string]V) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// ToSnakeCase converts PascalCase to snake_case.
func ToSnakeCase(s string) string {
	var result strings.Builder
	for i, r := range s {
		if i > 0 && unicode.IsUpper(r) {
			result.WriteRune('_')
		}
		result.WriteRune(unicode.ToLower(r))
	}
	return result.String()
}

// ToPascalCase converts snake_case to PascalCase.
func ToPascalCase(s string) string {
	words := regexp.MustCompile(`[_\-\s]+`).Split(s, -1)
	var result strings.Builder
	for _, word := range words {
		if len(word) > 0 {
			result.WriteString(strings.ToUpper(string(word[0])))
			if len(word) > 1 {
				result.WriteString(strings.ToLower(word[1:]))
			}
		}
	}
	return result.String()
}

// SanitizeGoName ensures a name is a valid Go identifier.
func SanitizeGoName(name string) string {
	// Remove invalid characters
	var result strings.Builder
	for i, r := range name {
		if i == 0 {
			if unicode.IsLetter(r) || r == '_' {
				result.WriteRune(r)
			} else {
				result.WriteRune('_')
			}
		} else {
			if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' {
				result.WriteRune(r)
			}
		}
	}

	s := result.String()
	if s == "" {
		return "_"
	}

	// Check for Go keywords
	if isGoKeyword(s) {
		return s + "_"
	}

	return s
}

var goKeywords = map[string]bool{
	"break": true, "case": true, "chan": true, "const": true, "continue": true,
	"default": true, "defer": true, "else": true, "fallthrough": true, "for": true,
	"func": true, "go": true, "goto": true, "if": true, "import": true,
	"interface": true, "map": true, "package": true, "range": true, "return": true,
	"select": true, "struct": true, "switch": true, "type": true, "var": true,
}

func isGoKeyword(s string) bool {
	return goKeywords[s]
}
