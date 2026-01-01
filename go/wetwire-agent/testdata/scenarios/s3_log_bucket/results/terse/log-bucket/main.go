package main

import (
	"github.com/wetwire/wetwire-aws/s3"
)

var LogArchiveBucket = s3.Bucket{
	BucketName: "log-archive-bucket",
	VersioningConfiguration: &s3.BucketVersioningConfiguration{
		Status: "Enabled",
	},
}