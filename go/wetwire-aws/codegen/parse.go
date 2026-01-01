package main

import (
	"sort"
	"strings"
)

// Service represents a group of resources for one AWS service.
type Service struct {
	Name          string                    // e.g., "s3"
	CFPrefix      string                    // e.g., "AWS::S3"
	Resources     map[string]ParsedResource // ResourceName -> Definition
	PropertyTypes map[string]ParsedProperty // PropertyName -> Definition
}

// ParsedResource is a parsed resource type.
type ParsedResource struct {
	Name          string                    // e.g., "Bucket"
	CFType        string                    // e.g., "AWS::S3::Bucket"
	Documentation string
	Properties    map[string]ParsedProperty
	Attributes    map[string]ParsedAttribute
}

// ParsedProperty is a parsed property.
type ParsedProperty struct {
	Name          string
	GoType        string
	CFType        string
	Documentation string
	Required      bool
	IsPointer     bool
	IsList        bool
	IsMap         bool
	ItemType      string
}

// ParsedAttribute is a parsed resource attribute (for GetAtt).
type ParsedAttribute struct {
	Name   string
	GoType string
}

// parseSpec organizes the CloudFormation spec by service.
func parseSpec(spec *CFSpec, filterService string) []*Service {
	services := make(map[string]*Service)

	// Parse resource types
	for cfType, resDef := range spec.ResourceTypes {
		// Parse AWS::S3::Bucket -> service=s3, name=Bucket
		parts := strings.Split(cfType, "::")
		if len(parts) != 3 || parts[0] != "AWS" {
			continue
		}

		serviceName := strings.ToLower(parts[1])
		resourceName := parts[2]

		// Filter by service if specified
		if filterService != "" && serviceName != filterService {
			continue
		}

		// Get or create service
		svc, ok := services[serviceName]
		if !ok {
			svc = &Service{
				Name:          serviceName,
				CFPrefix:      "AWS::" + parts[1],
				Resources:     make(map[string]ParsedResource),
				PropertyTypes: make(map[string]ParsedProperty),
			}
			services[serviceName] = svc
		}

		// Parse resource
		resource := ParsedResource{
			Name:          resourceName,
			CFType:        cfType,
			Documentation: resDef.Documentation,
			Properties:    make(map[string]ParsedProperty),
			Attributes:    make(map[string]ParsedAttribute),
		}

		// Parse properties
		for propName, propDef := range resDef.Properties {
			resource.Properties[propName] = parseProperty(propName, propDef)
		}

		// Parse attributes
		for attrName, attrDef := range resDef.Attributes {
			resource.Attributes[attrName] = ParsedAttribute{
				Name:   attrName,
				GoType: primitiveToGo(attrDef.PrimitiveType),
			}
		}

		svc.Resources[resourceName] = resource
	}

	// Parse property types and add to services
	for cfType, propDef := range spec.PropertyTypes {
		// Parse AWS::S3::Bucket.VersioningConfiguration
		parts := strings.Split(cfType, "::")
		if len(parts) != 3 || parts[0] != "AWS" {
			continue
		}

		// The property type name is after the dot
		dotParts := strings.SplitN(parts[2], ".", 2)
		if len(dotParts) != 2 {
			continue
		}

		serviceName := strings.ToLower(parts[1])
		propTypeName := dotParts[1]

		if filterService != "" && serviceName != filterService {
			continue
		}

		svc, ok := services[serviceName]
		if !ok {
			continue
		}

		// Parse as a nested struct
		parsed := ParsedProperty{
			Name:          propTypeName,
			GoType:        propTypeName,
			Documentation: propDef.Documentation,
		}

		svc.PropertyTypes[propTypeName] = parsed
	}

	// Convert to sorted slice
	result := make([]*Service, 0, len(services))
	for _, svc := range services {
		result = append(result, svc)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Name < result[j].Name
	})

	return result
}

// parseProperty converts a CloudFormation property definition to our parsed format.
func parseProperty(name string, def Property) ParsedProperty {
	prop := ParsedProperty{
		Name:          name,
		Documentation: def.Documentation,
		Required:      def.Required,
	}

	// Determine Go type
	if def.PrimitiveType != "" {
		prop.GoType = primitiveToGo(def.PrimitiveType)
		prop.CFType = def.PrimitiveType
	} else if def.Type == "List" {
		prop.IsList = true
		if def.PrimitiveItemType != "" {
			prop.ItemType = primitiveToGo(def.PrimitiveItemType)
		} else if def.ItemType != "" {
			prop.ItemType = def.ItemType
		} else {
			prop.ItemType = "any"
		}
		prop.GoType = "[]" + prop.ItemType
	} else if def.Type == "Map" {
		prop.IsMap = true
		if def.PrimitiveItemType != "" {
			prop.ItemType = primitiveToGo(def.PrimitiveItemType)
		} else if def.ItemType != "" {
			prop.ItemType = def.ItemType
		} else {
			prop.ItemType = "any"
		}
		prop.GoType = "map[string]" + prop.ItemType
	} else if def.Type != "" {
		// Reference to a property type
		prop.GoType = def.Type
		prop.CFType = def.Type
	} else {
		prop.GoType = "any"
	}

	// Non-required fields should be pointers (except slices/maps which are nil-able)
	if !def.Required && !prop.IsList && !prop.IsMap {
		prop.IsPointer = true
	}

	return prop
}

// primitiveToGo converts CloudFormation primitive types to Go types.
func primitiveToGo(cfType string) string {
	switch cfType {
	case "String":
		return "string"
	case "Integer":
		return "int"
	case "Long":
		return "int64"
	case "Double":
		return "float64"
	case "Boolean":
		return "bool"
	case "Timestamp":
		return "string" // ISO 8601 string
	case "Json":
		return "map[string]any"
	default:
		return "any"
	}
}
