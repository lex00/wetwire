package main

import (
	"compress/gzip"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
)

// CFSpec represents the CloudFormation Resource Specification.
type CFSpec struct {
	ResourceSpecificationVersion string                    `json:"ResourceSpecificationVersion"`
	ResourceTypes                map[string]ResourceType   `json:"ResourceTypes"`
	PropertyTypes                map[string]PropertyType   `json:"PropertyTypes"`
}

// ResourceType is a CloudFormation resource type definition.
type ResourceType struct {
	Documentation       string              `json:"Documentation"`
	Attributes          map[string]Attribute `json:"Attributes"`
	Properties          map[string]Property  `json:"Properties"`
	AdditionalProperties bool                `json:"AdditionalProperties"`
}

// PropertyType is a property type definition (nested structures).
type PropertyType struct {
	Documentation string              `json:"Documentation"`
	Properties    map[string]Property `json:"Properties"`
}

// Property is a property definition.
type Property struct {
	Documentation     string `json:"Documentation"`
	Required          bool   `json:"Required"`
	PrimitiveType     string `json:"PrimitiveType"`      // String, Integer, Boolean, etc.
	Type              string `json:"Type"`               // List, Map, or property type name
	ItemType          string `json:"ItemType"`           // For List/Map
	PrimitiveItemType string `json:"PrimitiveItemType"`  // For List/Map of primitives
	UpdateType        string `json:"UpdateType"`         // Mutable, Immutable, Conditional
	DuplicatesAllowed bool   `json:"DuplicatesAllowed"`
}

// Attribute is a resource attribute (for GetAtt).
type Attribute struct {
	PrimitiveType     string `json:"PrimitiveType"`
	Type              string `json:"Type"`
	PrimitiveItemType string `json:"PrimitiveItemType"`
	ItemType          string `json:"ItemType"`
}

// fetchSpec downloads and parses the CloudFormation spec.
func fetchSpec(url string, force bool) (*CFSpec, error) {
	// Check for cached spec
	cacheDir := filepath.Join(os.TempDir(), "wetwire-aws-codegen")
	cachePath := filepath.Join(cacheDir, "spec.json")

	if !force {
		if data, err := os.ReadFile(cachePath); err == nil {
			var spec CFSpec
			if err := json.Unmarshal(data, &spec); err == nil {
				fmt.Println("Using cached spec...")
				return &spec, nil
			}
		}
	}

	// Download the spec
	fmt.Printf("Downloading from %s...\n", url)
	resp, err := http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("downloading spec: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status: %s", resp.Status)
	}

	// Decompress gzip
	var reader io.Reader = resp.Body
	if resp.Header.Get("Content-Encoding") == "gzip" || filepath.Ext(url) == ".json" {
		// The URL says gzip, try to decompress
		gzReader, err := gzip.NewReader(resp.Body)
		if err != nil {
			// Not actually gzipped, use raw body
			resp.Body.Close()
			resp, err = http.Get(url)
			if err != nil {
				return nil, err
			}
			defer resp.Body.Close()
			reader = resp.Body
		} else {
			defer gzReader.Close()
			reader = gzReader
		}
	}

	data, err := io.ReadAll(reader)
	if err != nil {
		return nil, fmt.Errorf("reading spec: %w", err)
	}

	// Parse JSON
	var spec CFSpec
	if err := json.Unmarshal(data, &spec); err != nil {
		return nil, fmt.Errorf("parsing spec: %w", err)
	}

	// Cache the spec
	if err := os.MkdirAll(cacheDir, 0755); err == nil {
		_ = os.WriteFile(cachePath, data, 0644)
	}

	return &spec, nil
}
