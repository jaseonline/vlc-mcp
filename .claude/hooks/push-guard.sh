#!/usr/bin/env bash
# PreToolUse/Bash guard: ask before any git push that targets main.
# Several repos deploy on push to main (Workers Builds, release workflows), so a push is never silent.
# DEPLOY_PATHS narrows the prompt to pushes that touch deploy-relevant files (see stacks/cf-worker);
# empty means every push to main asks. Anything we can't evaluate falls back to asking.
DEPLOY_PATHS=''

cmd=$(jq -r '.tool_input.command // empty')
printf '%s' "$cmd" | grep -qE 'git( +-[^ ]+)* +push' || exit 0

d="${CLAUDE_PROJECT_DIR:-.}"
br=$(git -C "$d" branch --show-current 2>/dev/null)
printf '%s' "$cmd" | grep -qw main || [ "$br" = main ] || exit 0

reason="Pushing to main (could not check which files change)"
if [ "$br" = main ] && files=$(git -C "$d" diff --name-only '@{u}' HEAD 2>/dev/null); then
  if [ -n "$DEPLOY_PATHS" ]; then
    # Tree diff against upstream, so force-pushes are judged correctly too
    hits=$(printf '%s\n' "$files" | grep -E "$DEPLOY_PATHS" | paste -sd, -)
    [ -z "$hits" ] && exit 0
    reason="Pushing to main deploys to production: these commits change $hits"
  else
    reason="Pushing to main: $(printf '%s\n' "$files" | grep -c .) file(s) changed since upstream"
  fi
fi

jq -n --arg r "$reason" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"ask",permissionDecisionReason:$r}}'
