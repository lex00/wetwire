"""
Code generation for wetwire-aws.

This package contains the three-stage codegen pipeline:
- fetch: Download CloudFormation spec and botocore
- parse: Transform to intermediate format
- generate: Generate Python dataclasses
"""
