#!/bin/bash
# PreToolUse hook: require approval before ffmpeg writes any output file
# or whisperx runs (produces transcription files)

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // empty')

if [ "$tool_name" = "Bash" ]; then
  command=$(echo "$input" | jq -r '.tool_input.command // empty')

  if echo "$command" | grep -q 'ffmpeg'; then
    # Only auto-approve pure probe commands — contain -f null - and no output file with media extension.
    # Strip -i <input> first so the input filename doesn't match the output-extension check.
    # Handles piped probes: ffmpeg ... -f null - 2>&1 | grep "..."
    stripped=$(echo "$command" | sed 's/-i[[:space:]]\+[^[:space:]]\+//g')
    if echo "$command" | grep -qE '\-f null\s+\-' && ! echo "$stripped" | grep -qE '\.(mp4|mov|MOV|mkv|avi|wav|mp3|ass)\b'; then
      # Pure probe — auto-allow
      exit 0
    fi
    # Everything else (including commands that contain -f null but also write output) — ask
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"ffmpeg write operation — requires approval"}}'
    exit 0
  fi

fi
