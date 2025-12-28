"""CloudFormation parameter type constants.

These constants represent the built-in CloudFormation parameter types
that can be used in template parameter definitions.

Example:
    @wetwire_aws
    class MyParam:
        resource: Parameter
        type = STRING
        description = "A string parameter"
"""

# Basic parameter types
STRING = "String"
NUMBER = "Number"
LIST_NUMBER = "List<Number>"
COMMA_DELIMITED_LIST = "CommaDelimitedList"

# SSM Parameter types
SSM_PARAMETER_STRING = "AWS::SSM::Parameter::Value<String>"
SSM_PARAMETER_STRING_LIST = "AWS::SSM::Parameter::Value<List<String>>"

# AWS-specific parameter types
AVAILABILITY_ZONE = "AWS::EC2::AvailabilityZone::Name"
LIST_AVAILABILITY_ZONE = "List<AWS::EC2::AvailabilityZone::Name>"
AMI_ID = "AWS::EC2::Image::Id"
INSTANCE_ID = "AWS::EC2::Instance::Id"
KEY_PAIR = "AWS::EC2::KeyPair::KeyName"
SECURITY_GROUP_ID = "AWS::EC2::SecurityGroup::Id"
LIST_SECURITY_GROUP_ID = "List<AWS::EC2::SecurityGroup::Id>"
SUBNET_ID = "AWS::EC2::Subnet::Id"
LIST_SUBNET_ID = "List<AWS::EC2::Subnet::Id>"
VPC_ID = "AWS::EC2::VPC::Id"
VOLUME_ID = "AWS::EC2::Volume::Id"
HOSTED_ZONE_ID = "AWS::Route53::HostedZone::Id"
