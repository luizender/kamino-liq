#!/bin/bash
# PostToolUse hook: run ruff check --fix and ruff format on any Python file Claude
# edits or writes. Config is read from ruff.toml in the project root.
# Claude Code sends hook input as JSON on stdin: {"tool_input": {"file_path": "..."}}

fp=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")

if [[ "$fp" == *.py && "$fp" != *".venv"* && -n "$fp" ]]; then
    ruff="$CLAUDE_PROJECT_DIR/.venv/bin/ruff"
    # --unfixable F401,F811: never auto-remove imports during agentic edits. The
    # agent adds an import before the code that uses it; removing it mid-task would
    # break the next step. VS Code reads ruff.toml directly and still strips unused
    # imports on save, so nothing is lost.
    "$ruff" check --fix --unfixable F401,F811 "$fp" 2>&1 || true
    "$ruff" format "$fp" 2>&1
fi
