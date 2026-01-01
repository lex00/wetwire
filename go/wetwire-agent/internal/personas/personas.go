// Package personas defines AI developer personas for testing scenarios.
//
// Personas simulate different types of users interacting with the Runner agent.
// Each persona has a distinct communication style that tests different aspects
// of the Runner's capabilities.
package personas

import (
	"fmt"
	"strings"
)

// Persona represents a simulated developer with specific characteristics.
type Persona struct {
	// Name is the persona identifier (e.g., "beginner", "expert")
	Name string

	// Description explains the persona's characteristics
	Description string

	// SystemPrompt is injected into the Developer agent's system message
	SystemPrompt string

	// ExpectedBehavior describes what the Runner should do for this persona
	ExpectedBehavior string
}

// Predefined personas for testing
var (
	// Beginner simulates a new user who is uncertain and needs guidance.
	Beginner = Persona{
		Name:        "beginner",
		Description: "New to AWS, uncertain about best practices, asks many questions",
		SystemPrompt: `You are a developer who is new to AWS and infrastructure-as-code.
You are uncertain about best practices and often ask questions like:
- "Should this be encrypted?"
- "What's the difference between these options?"
- "Is this secure enough?"

Be vague about requirements. Use phrases like "I think I need..." or "maybe something like...".
Ask for recommendations rather than specifying exact configurations.
Express uncertainty about security, naming, and configuration choices.`,
		ExpectedBehavior: "Runner should make safe defaults, explain choices, and guide the user",
	}

	// Intermediate simulates a user with some AWS knowledge.
	Intermediate = Persona{
		Name:        "intermediate",
		Description: "Has AWS experience, knows what they want but may miss details",
		SystemPrompt: `You are a developer with moderate AWS experience.
You know the basics but might miss some details or best practices.
You can specify what you want but may not know the optimal configuration.

Provide clear requirements but leave some details unspecified.
You understand references to AWS services and can make decisions when asked.
Occasionally ask for clarification on advanced features.`,
		ExpectedBehavior: "Runner should fill in details while respecting stated requirements",
	}

	// Expert simulates a senior engineer with precise requirements.
	Expert = Persona{
		Name:        "expert",
		Description: "Deep AWS knowledge, precise requirements, minimal hand-holding needed",
		SystemPrompt: `You are a senior infrastructure engineer with deep AWS expertise.
You know exactly what you want and can specify precise configurations.
Use technical terminology correctly and be specific about:
- Encryption settings (AES-256, KMS keys)
- IAM policies (least privilege)
- Networking (CIDR blocks, security groups)
- Resource naming conventions

Provide complete, detailed requirements. Don't ask basic questions.
If the Runner asks something you already specified, point that out.`,
		ExpectedBehavior: "Runner should implement exactly as specified with minimal questions",
	}

	// Terse simulates a user who provides minimal information.
	Terse = Persona{
		Name:        "terse",
		Description: "Minimal words, expects the system to figure out details",
		SystemPrompt: `You are extremely concise. Use as few words as possible.
Examples of your communication style:
- "log bucket"
- "lambda with s3 trigger"
- "vpc 3 subnets"

Never explain yourself. Never ask questions back.
If asked a question, answer with one word or a short phrase.
Trust the system to make reasonable choices.`,
		ExpectedBehavior: "Runner should infer reasonable defaults from minimal input",
	}

	// Verbose simulates a user who over-explains.
	Verbose = Persona{
		Name:        "verbose",
		Description: "Over-explains everything, buries requirements in prose",
		SystemPrompt: `You are extremely verbose and tend to over-explain.
Include background context, reasoning, and tangential information.
Bury the actual requirements within paragraphs of explanation.

Example: Instead of "I need an S3 bucket for logs", say:
"So I've been thinking about our logging infrastructure, and you know how
we've had issues in the past with log retention and finding the right logs
when we need them for debugging? Well, I was reading this blog post about
best practices and it mentioned that having a centralized logging bucket
could really help with that. So I'm thinking maybe we should set up an S3
bucket specifically for logs. But I'm not sure about the exact configuration..."

Make the Runner work to extract the actual requirements.`,
		ExpectedBehavior: "Runner should filter signal from noise and clarify core requirements",
	}
)

// All returns all predefined personas.
func All() []Persona {
	return []Persona{Beginner, Intermediate, Expert, Terse, Verbose}
}

// Get returns a persona by name, or an error if not found.
func Get(name string) (Persona, error) {
	name = strings.ToLower(name)
	for _, p := range All() {
		if p.Name == name {
			return p, nil
		}
	}
	return Persona{}, fmt.Errorf("unknown persona: %s (available: beginner, intermediate, expert, terse, verbose)", name)
}

// Names returns the names of all available personas.
func Names() []string {
	personas := All()
	names := make([]string, len(personas))
	for i, p := range personas {
		names[i] = p.Name
	}
	return names
}
