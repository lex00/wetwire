package intrinsics

import (
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestRef_MarshalJSON(t *testing.T) {
	ref := Ref{"MyBucket"}
	data, err := json.Marshal(ref)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Ref": "MyBucket"}`, string(data))
}

func TestGetAtt_MarshalJSON(t *testing.T) {
	getAtt := GetAtt{"MyRole", "Arn"}
	data, err := json.Marshal(getAtt)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::GetAtt": ["MyRole", "Arn"]}`, string(data))
}

func TestSub_MarshalJSON(t *testing.T) {
	sub := Sub{"${AWS::Region}-bucket"}
	data, err := json.Marshal(sub)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::Sub": "${AWS::Region}-bucket"}`, string(data))
}

func TestSubWithMap_MarshalJSON(t *testing.T) {
	sub := SubWithMap{
		String: "${Bucket}-data",
		Variables: map[string]any{
			"Bucket": Ref{"MyBucket"},
		},
	}
	data, err := json.Marshal(sub)
	require.NoError(t, err)
	// The nested Ref should also be serialized correctly
	assert.Contains(t, string(data), `"Fn::Sub"`)
	assert.Contains(t, string(data), `"${Bucket}-data"`)
}

func TestJoin_MarshalJSON(t *testing.T) {
	join := Join{",", []any{"a", "b", "c"}}
	data, err := json.Marshal(join)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::Join": [",", ["a", "b", "c"]]}`, string(data))
}

func TestSelect_MarshalJSON(t *testing.T) {
	sel := Select{0, GetAZs{""}}
	data, err := json.Marshal(sel)
	require.NoError(t, err)
	assert.Contains(t, string(data), `"Fn::Select"`)
	assert.Contains(t, string(data), `"Fn::GetAZs"`)
}

func TestGetAZs_MarshalJSON(t *testing.T) {
	azs := GetAZs{""}
	data, err := json.Marshal(azs)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::GetAZs": ""}`, string(data))

	azs = GetAZs{"us-east-1"}
	data, err = json.Marshal(azs)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::GetAZs": "us-east-1"}`, string(data))
}

func TestIf_MarshalJSON(t *testing.T) {
	ifExpr := If{"CreateBucket", "yes", "no"}
	data, err := json.Marshal(ifExpr)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::If": ["CreateBucket", "yes", "no"]}`, string(data))
}

func TestEquals_MarshalJSON(t *testing.T) {
	eq := Equals{Ref{"Env"}, "prod"}
	data, err := json.Marshal(eq)
	require.NoError(t, err)
	assert.Contains(t, string(data), `"Fn::Equals"`)
}

func TestAnd_MarshalJSON(t *testing.T) {
	and := And{[]any{
		Equals{Ref{"Env"}, "prod"},
		Equals{Ref{"Region"}, "us-east-1"},
	}}
	data, err := json.Marshal(and)
	require.NoError(t, err)
	assert.Contains(t, string(data), `"Fn::And"`)
}

func TestOr_MarshalJSON(t *testing.T) {
	or := Or{[]any{
		Equals{Ref{"Env"}, "prod"},
		Equals{Ref{"Env"}, "staging"},
	}}
	data, err := json.Marshal(or)
	require.NoError(t, err)
	assert.Contains(t, string(data), `"Fn::Or"`)
}

func TestNot_MarshalJSON(t *testing.T) {
	not := Not{Equals{Ref{"Env"}, "dev"}}
	data, err := json.Marshal(not)
	require.NoError(t, err)
	assert.Contains(t, string(data), `"Fn::Not"`)
}

func TestBase64_MarshalJSON(t *testing.T) {
	b64 := Base64{"Hello, World!"}
	data, err := json.Marshal(b64)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::Base64": "Hello, World!"}`, string(data))
}

func TestImportValue_MarshalJSON(t *testing.T) {
	imp := ImportValue{"SharedVPC"}
	data, err := json.Marshal(imp)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::ImportValue": "SharedVPC"}`, string(data))
}

func TestFindInMap_MarshalJSON(t *testing.T) {
	fim := FindInMap{"RegionMap", Ref{"AWS::Region"}, "AMI"}
	data, err := json.Marshal(fim)
	require.NoError(t, err)
	assert.Contains(t, string(data), `"Fn::FindInMap"`)
}

func TestSplit_MarshalJSON(t *testing.T) {
	split := Split{",", "a,b,c"}
	data, err := json.Marshal(split)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::Split": [",", "a,b,c"]}`, string(data))
}

func TestCidr_MarshalJSON(t *testing.T) {
	cidr := Cidr{"10.0.0.0/16", 6, 8}
	data, err := json.Marshal(cidr)
	require.NoError(t, err)
	assert.JSONEq(t, `{"Fn::Cidr": ["10.0.0.0/16", 6, 8]}`, string(data))
}

func TestPseudoParameters(t *testing.T) {
	// Test that pseudo-parameters serialize correctly
	tests := []struct {
		name     string
		param    Ref
		expected string
	}{
		{"AWS_REGION", AWS_REGION, `{"Ref": "AWS::Region"}`},
		{"AWS_ACCOUNT_ID", AWS_ACCOUNT_ID, `{"Ref": "AWS::AccountId"}`},
		{"AWS_STACK_NAME", AWS_STACK_NAME, `{"Ref": "AWS::StackName"}`},
		{"AWS_STACK_ID", AWS_STACK_ID, `{"Ref": "AWS::StackId"}`},
		{"AWS_PARTITION", AWS_PARTITION, `{"Ref": "AWS::Partition"}`},
		{"AWS_URL_SUFFIX", AWS_URL_SUFFIX, `{"Ref": "AWS::URLSuffix"}`},
		{"AWS_NO_VALUE", AWS_NO_VALUE, `{"Ref": "AWS::NoValue"}`},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			data, err := json.Marshal(tt.param)
			require.NoError(t, err)
			assert.JSONEq(t, tt.expected, string(data))
		})
	}
}
