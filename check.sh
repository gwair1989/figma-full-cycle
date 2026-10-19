#!/usr/bin/env bash
# Local checks for this repository. Run before pushing.
#
#   ./check.sh              run everything
#   ./check.sh --quick      skip the extra interpreter versions
#
# Validator tests deliberately run on every Python 3 interpreter found on the
# machine: the skill claims to work on the system python3 (3.9 on Xcode CLT),
# and that claim is only worth what it is actually tested against.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$REPO_ROOT/skills/figma-full-cycle/scripts/tests"
QUICK=0
FAILED=()

[ "${1:-}" = "--quick" ] && QUICK=1

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
record() { [ "$1" -eq 0 ] || FAILED+=("$2"); }

# Collect one interpreter per distinct Python 3 minor version.
interpreters() {
  local seen="" candidate version
  # /usr/bin/python3 is listed explicitly: on macOS it is the Xcode Command Line
  # Tools interpreter (3.9), which a $PATH lookup shadows with Homebrew's python3.
  for candidate in python3 /usr/bin/python3 python3.9 python3.10 python3.11 python3.12 python3.13 python3.14; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    version="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)" || continue
    case " $seen " in *" $version "*) continue ;; esac
    seen="$seen $version"
    printf '%s\t%s\n' "$candidate" "$version"
    [ "$QUICK" -eq 1 ] && break
  done
}

while IFS=$'\t' read -r interpreter version; do
  for test in "$TESTS_DIR"/test_*.py; do
    step "$(basename "$test") — Python $version ($interpreter)"
    "$interpreter" "$test"
    record $? "$(basename "$test") (python $version)"
  done
  step "Package and installer tests — Python $version ($interpreter)"
  "$interpreter" -m unittest discover -s "$REPO_ROOT/tools/tests"
  record $? "package and installer tests (python $version)"
done < <(interpreters)

step "Device screenshot evidence recorder — Node.js 22+"
if command -v node >/dev/null 2>&1 && node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)'; then
  node --test "$REPO_ROOT/skills/device-usage/scripts/capture-evidence.test.mjs"
  record $? "capture-evidence.test.mjs"
else
  printf '%s\n' "Node.js 22+ is required to run the device evidence helper tests." >&2
  record 1 "Node.js 22+ unavailable"
fi

step "Skill structure"
python3 "$REPO_ROOT/tools/lint_skills.py"
record $? "lint_skills.py"

step "install.sh syntax"
bash -n "$REPO_ROOT/install.sh" && echo "OK"
record $? "install.sh syntax"

if [ ${#FAILED[@]} -gt 0 ]; then
  printf '\n\033[31mFAILED:\033[0m %s\n' "${FAILED[*]}"
  exit 1
fi

printf '\n\033[32mAll checks passed.\033[0m\n'
