// Package results tracks session results and generates RESULTS.md files.
//
// Each session produces a RESULTS.md file containing:
// - Session metadata (persona, scenario, timestamp)
// - Complete conversation log
// - Lint cycles and fixes
// - Final score breakdown
// - Improvement suggestions
package results

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/lex00/wetwire-agent/internal/scoring"
)

// Message represents a single message in the conversation.
type Message struct {
	Role      string    `json:"role"`      // "developer", "runner", "system"
	Content   string    `json:"content"`
	Timestamp time.Time `json:"timestamp"`
	ToolCalls []ToolCall `json:"tool_calls,omitempty"`
}

// ToolCall represents a tool invocation by the agent.
type ToolCall struct {
	Name   string `json:"name"`
	Input  string `json:"input"`
	Output string `json:"output"`
}

// LintCycle represents one cycle of lint/fix.
type LintCycle struct {
	Cycle      int      `json:"cycle"`
	IssueCount int      `json:"issue_count"`
	Issues     []string `json:"issues"`
	FixedCount int      `json:"fixed_count"`
	Passed     bool     `json:"passed"`
}

// Question represents a clarifying question from the Runner.
type Question struct {
	Question string `json:"question"`
	Answer   string `json:"answer"`
}

// Session contains all data for a single agent session.
type Session struct {
	// Metadata
	ID        string    `json:"id"`
	Persona   string    `json:"persona"`
	Scenario  string    `json:"scenario"`
	StartTime time.Time `json:"start_time"`
	EndTime   time.Time `json:"end_time"`

	// Prompt
	InitialPrompt string `json:"initial_prompt"`

	// Conversation
	Messages  []Message  `json:"messages"`
	Questions []Question `json:"questions"`

	// Lint cycles
	LintCycles []LintCycle `json:"lint_cycles"`

	// Output
	GeneratedFiles []string `json:"generated_files"`
	TemplateJSON   string   `json:"template_json,omitempty"`

	// Scoring
	Score *scoring.Score `json:"score,omitempty"`

	// Suggestions for framework improvement
	Suggestions []string `json:"suggestions,omitempty"`
}

// NewSession creates a new session with the given metadata.
func NewSession(persona, scenario string) *Session {
	return &Session{
		ID:        generateID(),
		Persona:   persona,
		Scenario:  scenario,
		StartTime: time.Now(),
		Messages:  make([]Message, 0),
		Questions: make([]Question, 0),
		LintCycles: make([]LintCycle, 0),
	}
}

// AddMessage adds a message to the conversation log.
func (s *Session) AddMessage(role, content string) {
	s.Messages = append(s.Messages, Message{
		Role:      role,
		Content:   content,
		Timestamp: time.Now(),
	})
}

// AddQuestion adds a clarifying question and answer.
func (s *Session) AddQuestion(question, answer string) {
	s.Questions = append(s.Questions, Question{
		Question: question,
		Answer:   answer,
	})
}

// AddLintCycle adds a lint cycle result.
func (s *Session) AddLintCycle(issues []string, fixed int, passed bool) {
	s.LintCycles = append(s.LintCycles, LintCycle{
		Cycle:      len(s.LintCycles) + 1,
		IssueCount: len(issues),
		Issues:     issues,
		FixedCount: fixed,
		Passed:     passed,
	})
}

// Complete marks the session as complete and calculates the final score.
func (s *Session) Complete() {
	s.EndTime = time.Now()
}

// Duration returns the session duration.
func (s *Session) Duration() time.Duration {
	if s.EndTime.IsZero() {
		return time.Since(s.StartTime)
	}
	return s.EndTime.Sub(s.StartTime)
}

// Writer writes session results to files.
type Writer struct {
	OutputDir string
}

// NewWriter creates a new results writer.
func NewWriter(outputDir string) *Writer {
	return &Writer{OutputDir: outputDir}
}

// Write writes the session results to files.
func (w *Writer) Write(session *Session) error {
	// Create output directory
	dir := filepath.Join(w.OutputDir, session.Persona)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("creating output directory: %w", err)
	}

	// Write RESULTS.md
	md := w.formatMarkdown(session)
	mdPath := filepath.Join(dir, "RESULTS.md")
	if err := os.WriteFile(mdPath, []byte(md), 0644); err != nil {
		return fmt.Errorf("writing RESULTS.md: %w", err)
	}

	// Write session.json
	jsonData, err := json.MarshalIndent(session, "", "  ")
	if err != nil {
		return fmt.Errorf("marshaling session: %w", err)
	}
	jsonPath := filepath.Join(dir, "session.json")
	if err := os.WriteFile(jsonPath, jsonData, 0644); err != nil {
		return fmt.Errorf("writing session.json: %w", err)
	}

	// Write score.json if available
	if session.Score != nil {
		scoreData, err := json.MarshalIndent(session.Score, "", "  ")
		if err != nil {
			return fmt.Errorf("marshaling score: %w", err)
		}
		scorePath := filepath.Join(dir, "score.json")
		if err := os.WriteFile(scorePath, scoreData, 0644); err != nil {
			return fmt.Errorf("writing score.json: %w", err)
		}
	}

	return nil
}

// formatMarkdown generates the RESULTS.md content.
func (w *Writer) formatMarkdown(s *Session) string {
	var b strings.Builder

	// Header
	b.WriteString(fmt.Sprintf("# Session Results: %s\n\n", s.ID))
	b.WriteString(fmt.Sprintf("**Persona:** %s\n", s.Persona))
	b.WriteString(fmt.Sprintf("**Scenario:** %s\n", s.Scenario))
	b.WriteString(fmt.Sprintf("**Duration:** %s\n", s.Duration().Round(time.Second)))
	b.WriteString(fmt.Sprintf("**Timestamp:** %s\n\n", s.StartTime.Format(time.RFC3339)))

	// Score summary
	if s.Score != nil {
		b.WriteString("## Score\n\n")
		b.WriteString(fmt.Sprintf("**Total:** %d/15 (%s)\n\n", s.Score.Total(), s.Score.Threshold()))
		b.WriteString("| Dimension | Score | Notes |\n")
		b.WriteString("|-----------|-------|-------|\n")
		dims := []scoring.Dimension{
			s.Score.Completeness,
			s.Score.LintQuality,
			s.Score.CodeQuality,
			s.Score.OutputValidity,
			s.Score.QuestionEfficiency,
		}
		for _, d := range dims {
			b.WriteString(fmt.Sprintf("| %s | %d | %s |\n", d.Name, d.Rating, d.Notes))
		}
		b.WriteString("\n")
	}

	// Initial prompt
	b.WriteString("## Initial Prompt\n\n")
	b.WriteString("```\n")
	b.WriteString(s.InitialPrompt)
	b.WriteString("\n```\n\n")

	// Clarifying questions
	if len(s.Questions) > 0 {
		b.WriteString("## Clarifying Questions\n\n")
		for i, q := range s.Questions {
			b.WriteString(fmt.Sprintf("### Question %d\n\n", i+1))
			b.WriteString(fmt.Sprintf("**Runner:** %s\n\n", q.Question))
			b.WriteString(fmt.Sprintf("**Developer:** %s\n\n", q.Answer))
		}
	}

	// Lint cycles
	if len(s.LintCycles) > 0 {
		b.WriteString("## Lint Cycles\n\n")
		for _, lc := range s.LintCycles {
			status := "Failed"
			if lc.Passed {
				status = "Passed"
			}
			b.WriteString(fmt.Sprintf("### Cycle %d (%s)\n\n", lc.Cycle, status))
			b.WriteString(fmt.Sprintf("- Issues found: %d\n", lc.IssueCount))
			b.WriteString(fmt.Sprintf("- Issues fixed: %d\n\n", lc.FixedCount))
			if len(lc.Issues) > 0 {
				b.WriteString("Issues:\n")
				for _, issue := range lc.Issues {
					b.WriteString(fmt.Sprintf("- %s\n", issue))
				}
				b.WriteString("\n")
			}
		}
	}

	// Generated files
	if len(s.GeneratedFiles) > 0 {
		b.WriteString("## Generated Files\n\n")
		for _, f := range s.GeneratedFiles {
			b.WriteString(fmt.Sprintf("- `%s`\n", f))
		}
		b.WriteString("\n")
	}

	// Conversation log
	b.WriteString("## Conversation Log\n\n")
	for _, msg := range s.Messages {
		b.WriteString(fmt.Sprintf("### %s (%s)\n\n", msg.Role, msg.Timestamp.Format("15:04:05")))
		b.WriteString(msg.Content)
		b.WriteString("\n\n")
		if len(msg.ToolCalls) > 0 {
			b.WriteString("**Tool Calls:**\n\n")
			for _, tc := range msg.ToolCalls {
				b.WriteString(fmt.Sprintf("- `%s`\n", tc.Name))
			}
			b.WriteString("\n")
		}
	}

	// Suggestions
	if len(s.Suggestions) > 0 {
		b.WriteString("## Improvement Suggestions\n\n")
		for _, sug := range s.Suggestions {
			b.WriteString(fmt.Sprintf("- %s\n", sug))
		}
		b.WriteString("\n")
	}

	return b.String()
}

// generateID creates a unique session ID.
func generateID() string {
	return fmt.Sprintf("session_%s", time.Now().Format("20060102_150405"))
}
