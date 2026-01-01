package agents

import (
	"testing"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/stretchr/testify/assert"
)

func TestCheckLintEnforcement_WriteWithoutLint(t *testing.T) {
	r := &RunnerAgent{}

	// write_file called without run_lint
	toolsCalled := []string{"write_file"}
	msg := r.checkLintEnforcement(toolsCalled)

	assert.NotEmpty(t, msg)
	assert.Contains(t, msg, "ENFORCEMENT")
	assert.Contains(t, msg, "run_lint")
}

func TestCheckLintEnforcement_WriteWithLint(t *testing.T) {
	r := &RunnerAgent{}

	// write_file called with run_lint in same turn
	toolsCalled := []string{"write_file", "run_lint"}
	msg := r.checkLintEnforcement(toolsCalled)

	assert.Empty(t, msg)
}

func TestCheckLintEnforcement_LintOnly(t *testing.T) {
	r := &RunnerAgent{}

	// Only run_lint called
	toolsCalled := []string{"run_lint"}
	msg := r.checkLintEnforcement(toolsCalled)

	assert.Empty(t, msg)
}

func TestCheckLintEnforcement_ReadFile(t *testing.T) {
	r := &RunnerAgent{}

	// read_file doesn't trigger enforcement
	toolsCalled := []string{"read_file"}
	msg := r.checkLintEnforcement(toolsCalled)

	assert.Empty(t, msg)
}

func TestCheckLintEnforcement_MultipleWrites(t *testing.T) {
	r := &RunnerAgent{}

	// Multiple writes with lint at end
	toolsCalled := []string{"write_file", "write_file", "run_lint"}
	msg := r.checkLintEnforcement(toolsCalled)

	assert.Empty(t, msg)
}

func TestCheckCompletionGate_NoFiles(t *testing.T) {
	r := &RunnerAgent{
		generatedFiles: []string{},
		lintCalled:     false,
		lintPassed:     false,
		pendingLint:    false,
	}

	// No files written yet, allow continuation
	resp := &anthropic.Message{
		Content: []anthropic.ContentBlockUnion{
			{Type: "text", Text: "Let me think about this..."},
		},
	}
	msg := r.checkCompletionGate(resp)

	assert.Empty(t, msg)
}

func TestCheckCompletionGate_LintNotCalled(t *testing.T) {
	r := &RunnerAgent{
		generatedFiles: []string{"main.go"},
		lintCalled:     false,
		lintPassed:     false,
		pendingLint:    false,
	}

	resp := &anthropic.Message{
		Content: []anthropic.ContentBlockUnion{
			{Type: "text", Text: "I'm done with the code."},
		},
	}
	msg := r.checkCompletionGate(resp)

	assert.NotEmpty(t, msg)
	assert.Contains(t, msg, "ENFORCEMENT")
	assert.Contains(t, msg, "run_lint")
}

func TestCheckCompletionGate_PendingLint(t *testing.T) {
	r := &RunnerAgent{
		generatedFiles: []string{"main.go"},
		lintCalled:     true,
		lintPassed:     true,
		pendingLint:    true, // Code changed since last lint
	}

	resp := &anthropic.Message{
		Content: []anthropic.ContentBlockUnion{
			{Type: "text", Text: "The task is complete."},
		},
	}
	msg := r.checkCompletionGate(resp)

	assert.NotEmpty(t, msg)
	assert.Contains(t, msg, "ENFORCEMENT")
	assert.Contains(t, msg, "written code since")
}

func TestCheckCompletionGate_LintFailed(t *testing.T) {
	r := &RunnerAgent{
		generatedFiles: []string{"main.go"},
		lintCalled:     true,
		lintPassed:     false,
		pendingLint:    false,
	}

	resp := &anthropic.Message{
		Content: []anthropic.ContentBlockUnion{
			{Type: "text", Text: "All done!"},
		},
	}
	msg := r.checkCompletionGate(resp)

	assert.NotEmpty(t, msg)
	assert.Contains(t, msg, "ENFORCEMENT")
	assert.Contains(t, msg, "issues")
}

func TestCheckCompletionGate_AllGatesPassed(t *testing.T) {
	r := &RunnerAgent{
		generatedFiles: []string{"main.go"},
		lintCalled:     true,
		lintPassed:     true,
		pendingLint:    false,
	}

	resp := &anthropic.Message{
		Content: []anthropic.ContentBlockUnion{
			{Type: "text", Text: "Everything is finished and working."},
		},
	}
	msg := r.checkCompletionGate(resp)

	assert.Empty(t, msg)
}

func TestCheckCompletionGate_CompletionKeywords(t *testing.T) {
	tests := []struct {
		name string
		text string
	}{
		{"done", "I'm done."},
		{"complete", "The task is complete."},
		{"finished", "I have finished the work."},
		{"that's it", "That's it for now."},
		{"all set", "You're all set!"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r := &RunnerAgent{
				generatedFiles: []string{"main.go"},
				lintCalled:     false, // Should trigger enforcement
				lintPassed:     false,
				pendingLint:    false,
			}

			resp := &anthropic.Message{
				Content: []anthropic.ContentBlockUnion{
					{Type: "text", Text: tt.text},
				},
			}
			msg := r.checkCompletionGate(resp)

			assert.NotEmpty(t, msg, "Should enforce for completion keyword: %s", tt.name)
		})
	}
}

func TestToolWriteFile_UpdatesState(t *testing.T) {
	dir := t.TempDir()
	r := &RunnerAgent{
		workDir:     dir,
		lintPassed:  true, // Should be reset
		pendingLint: false,
	}

	result := r.toolWriteFile("test.go", "package main")

	assert.Contains(t, result, "Wrote")
	assert.True(t, r.pendingLint, "pendingLint should be true after write")
	assert.False(t, r.lintPassed, "lintPassed should be false after write")
	assert.Contains(t, r.generatedFiles, "test.go")
}

func TestToolWriteFile_CreatesDirectories(t *testing.T) {
	dir := t.TempDir()
	r := &RunnerAgent{workDir: dir}

	result := r.toolWriteFile("nested/dir/test.go", "package main")

	assert.Contains(t, result, "Wrote")
	assert.Contains(t, r.generatedFiles, "nested/dir/test.go")
}

func TestGetLintCycles(t *testing.T) {
	r := &RunnerAgent{lintCycles: 3}
	assert.Equal(t, 3, r.GetLintCycles())
}

func TestLintPassed(t *testing.T) {
	r := &RunnerAgent{lintPassed: true}
	assert.True(t, r.LintPassed())

	r.lintPassed = false
	assert.False(t, r.LintPassed())
}

func TestGetGeneratedFiles(t *testing.T) {
	r := &RunnerAgent{
		generatedFiles: []string{"a.go", "b.go"},
	}
	files := r.GetGeneratedFiles()

	assert.Equal(t, []string{"a.go", "b.go"}, files)
}

func TestGetTemplate(t *testing.T) {
	r := &RunnerAgent{
		templateJSON: `{"Resources": {}}`,
	}
	assert.Equal(t, `{"Resources": {}}`, r.GetTemplate())
}
