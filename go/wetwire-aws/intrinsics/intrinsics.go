// Package intrinsics provides CloudFormation intrinsic functions.
//
// These types serialize to CloudFormation's intrinsic function syntax:
//
//	Ref{"MyBucket"} → {"Ref": "MyBucket"}
//	Sub{"${AWS::Region}-bucket"} → {"Fn::Sub": "${AWS::Region}-bucket"}
//	Join{",", []any{"a", "b"}} → {"Fn::Join": [",", ["a", "b"]]}
package intrinsics

import (
	"encoding/json"
)

// Ref represents a CloudFormation Ref intrinsic function.
// Use this for referencing parameters or getting a resource's default return value.
//
// Example:
//
//	Ref{"MyParameter"}  → {"Ref": "MyParameter"}
//	Ref{"MyBucket"}     → {"Ref": "MyBucket"}
type Ref struct {
	LogicalName string
}

// MarshalJSON serializes to CloudFormation Ref syntax.
func (r Ref) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]string{
		"Ref": r.LogicalName,
	})
}

// Param creates a Ref for a CloudFormation parameter.
// This makes it explicit that the reference is to a parameter, not a resource.
//
// Example:
//
//	var VpcId = Param("VpcId")     // declare parameter
//	VpcId: VpcId,                  // use in resource - type-safe
func Param(name string) Ref {
	return Ref{LogicalName: name}
}

// GetAtt represents a CloudFormation Fn::GetAtt intrinsic function.
// Use this for getting a specific attribute from a resource.
//
// Example:
//
//	GetAtt{"MyBucket", "Arn"} → {"Fn::GetAtt": ["MyBucket", "Arn"]}
type GetAtt struct {
	LogicalName string
	Attribute   string
}

// MarshalJSON serializes to CloudFormation GetAtt syntax.
func (g GetAtt) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]string{
		"Fn::GetAtt": {g.LogicalName, g.Attribute},
	})
}

// Sub represents a CloudFormation Fn::Sub intrinsic function.
// Substitutes variables in a string.
//
// Examples:
//
//	Sub{"${AWS::Region}-bucket"} → {"Fn::Sub": "${AWS::Region}-bucket"}
//	SubWithMap{"${Bucket}-data", map[string]any{"Bucket": Ref{"MyBucket"}}}
type Sub struct {
	String string
}

// MarshalJSON serializes to CloudFormation Sub syntax.
func (s Sub) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]string{
		"Fn::Sub": s.String,
	})
}

// SubWithMap is Fn::Sub with a variable map.
type SubWithMap struct {
	String    string
	Variables map[string]any
}

// MarshalJSON serializes to CloudFormation Sub syntax with variables.
func (s SubWithMap) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::Sub": {s.String, s.Variables},
	})
}

// Join represents a CloudFormation Fn::Join intrinsic function.
//
// Example:
//
//	Join{",", []any{"a", "b", "c"}} → {"Fn::Join": [",", ["a", "b", "c"]]}
type Join struct {
	Delimiter string
	Values    []any
}

// MarshalJSON serializes to CloudFormation Join syntax.
func (j Join) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::Join": {j.Delimiter, j.Values},
	})
}

// Select represents a CloudFormation Fn::Select intrinsic function.
//
// Example:
//
//	Select{0, GetAZs{""}} → {"Fn::Select": [0, {"Fn::GetAZs": ""}]}
type Select struct {
	Index int
	List  any
}

// MarshalJSON serializes to CloudFormation Select syntax.
func (s Select) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::Select": {s.Index, s.List},
	})
}

// GetAZs represents a CloudFormation Fn::GetAZs intrinsic function.
//
// Example:
//
//	GetAZs{""} → {"Fn::GetAZs": ""} (current region)
//	GetAZs{"us-east-1"} → {"Fn::GetAZs": "us-east-1"}
type GetAZs struct {
	Region string
}

// MarshalJSON serializes to CloudFormation GetAZs syntax.
func (g GetAZs) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]string{
		"Fn::GetAZs": g.Region,
	})
}

// If represents a CloudFormation Fn::If intrinsic function.
//
// Example:
//
//	If{"CreateResources", "yes", "no"}
type If struct {
	Condition   string
	ValueIfTrue any
	ValueIfFalse any
}

// MarshalJSON serializes to CloudFormation If syntax.
func (i If) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::If": {i.Condition, i.ValueIfTrue, i.ValueIfFalse},
	})
}

// Equals represents a CloudFormation Fn::Equals condition function.
type Equals struct {
	Value1 any
	Value2 any
}

// MarshalJSON serializes to CloudFormation Equals syntax.
func (e Equals) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::Equals": {e.Value1, e.Value2},
	})
}

// And represents a CloudFormation Fn::And condition function.
type And struct {
	Conditions []any
}

// MarshalJSON serializes to CloudFormation And syntax.
func (a And) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::And": a.Conditions,
	})
}

// Or represents a CloudFormation Fn::Or condition function.
type Or struct {
	Conditions []any
}

// MarshalJSON serializes to CloudFormation Or syntax.
func (o Or) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::Or": o.Conditions,
	})
}

// Not represents a CloudFormation Fn::Not condition function.
type Not struct {
	Condition any
}

// MarshalJSON serializes to CloudFormation Not syntax.
func (n Not) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::Not": {n.Condition},
	})
}

// Base64 represents a CloudFormation Fn::Base64 intrinsic function.
type Base64 struct {
	Value any
}

// MarshalJSON serializes to CloudFormation Base64 syntax.
func (b Base64) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]any{
		"Fn::Base64": b.Value,
	})
}

// ImportValue represents a CloudFormation Fn::ImportValue intrinsic function.
type ImportValue struct {
	ExportName any
}

// MarshalJSON serializes to CloudFormation ImportValue syntax.
func (i ImportValue) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]any{
		"Fn::ImportValue": i.ExportName,
	})
}

// FindInMap represents a CloudFormation Fn::FindInMap intrinsic function.
type FindInMap struct {
	MapName   string
	TopKey    any
	SecondKey any
}

// MarshalJSON serializes to CloudFormation FindInMap syntax.
func (f FindInMap) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::FindInMap": {f.MapName, f.TopKey, f.SecondKey},
	})
}

// Split represents a CloudFormation Fn::Split intrinsic function.
type Split struct {
	Delimiter string
	Source    any
}

// MarshalJSON serializes to CloudFormation Split syntax.
func (s Split) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::Split": {s.Delimiter, s.Source},
	})
}

// Cidr represents a CloudFormation Fn::Cidr intrinsic function.
type Cidr struct {
	IPBlock  any
	Count    any
	CidrBits any
}

// MarshalJSON serializes to CloudFormation Cidr syntax.
func (c Cidr) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string][]any{
		"Fn::Cidr": {c.IPBlock, c.Count, c.CidrBits},
	})
}

// Condition represents a CloudFormation Condition reference.
// Used in resource Condition fields.
type Condition struct {
	Name string
}

// MarshalJSON serializes to CloudFormation Condition syntax.
func (c Condition) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]string{
		"Condition": c.Name,
	})
}

// Tag represents a CloudFormation resource tag.
// This is a common type used across many AWS resources.
//
// Example:
//
//	Tag{Key: "Name", Value: "my-resource"}
//	Tag{Key: "Environment", Value: Sub{"${Environment}"}}
type Tag struct {
	Key   string
	Value any
}

// MarshalJSON serializes to CloudFormation tag syntax.
func (t Tag) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]any{
		"Key":   t.Key,
		"Value": t.Value,
	})
}

// Transform represents a CloudFormation Fn::Transform intrinsic function.
type Transform struct {
	Name       string
	Parameters map[string]any
}

// MarshalJSON serializes to CloudFormation Transform syntax.
func (t Transform) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]any{
		"Fn::Transform": map[string]any{
			"Name":       t.Name,
			"Parameters": t.Parameters,
		},
	})
}

// Output represents a CloudFormation stack output.
//
// Example:
//
//	var BucketArnOutput = Output{
//	    Value:       MyBucket.Arn,
//	    Description: "The ARN of the bucket",
//	    ExportName:  Sub{"${AWS::StackName}-BucketArn"},
//	}
type Output struct {
	Value       any
	Description string
	ExportName  any // optional, for cross-stack references
	Condition   string // optional, conditional output
}

// MarshalJSON serializes to CloudFormation output syntax.
func (o Output) MarshalJSON() ([]byte, error) {
	result := map[string]any{
		"Value": o.Value,
	}
	if o.Description != "" {
		result["Description"] = o.Description
	}
	if o.ExportName != nil {
		result["Export"] = map[string]any{"Name": o.ExportName}
	}
	if o.Condition != "" {
		result["Condition"] = o.Condition
	}
	return json.Marshal(result)
}
