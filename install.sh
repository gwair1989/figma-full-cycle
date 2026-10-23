#!/usr/bin/env bash
# Install the skills in this repository into an agent's skills directory.
#
#   ./install.sh                          symlink into ~/.claude/skills
#   ./install.sh --target ~/.codex/skills install for Codex
#   ./install.sh --target .claude/skills  install for the current project only
#   ./install.sh --skill device-usage     install one skill (repeatable)
#   ./install.sh --copy                   copy instead of symlinking
#   ./install.sh --force                  replace an existing entry; the old one is moved
#                                         to ../.skill-backups next to the target directory
#   ./install.sh --uninstall              remove entries this script installed
#
# Symlinks are the default: `git pull` then updates the installed skills in place.
# Selecting figma-full-cycle also installs its four required companions.
# Visual workflows include one _figma-full-cycle-shared resource directory (not a skill).
# Uninstall removes only selected entries, never shared dependencies implicitly.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$REPO_ROOT/skills"
SHARED_NAME="_figma-full-cycle-shared"
TARGET="${HOME}/.claude/skills"
MODE="symlink"
FORCE=0
UNINSTALL=0
SELECTED_SKILLS=()

log()  { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target)    TARGET="${2:?--target needs a path}"; shift 2 ;;
    --target=*)  TARGET="${1#*=}"; shift ;;
    --skill)     SELECTED_SKILLS+=("${2:?--skill needs a name}"); shift 2 ;;
    --skill=*)   SELECTED_SKILLS+=("${1#*=}"); shift ;;
    --copy)      MODE="copy"; shift ;;
    --force)     FORCE=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help)   sed -n '2,/^set -euo pipefail/{ /^set -euo pipefail/d; s/^# \{0,1\}//; p; }' "${BASH_SOURCE[0]}"; exit 0 ;;
    *)           die "unknown option: $1 (try --help)" ;;
  esac
done

[ -d "$SRC_DIR" ] || die "no skills/ directory next to install.sh"

# Expand a leading ~ and resolve the target, following it if it is itself a symlink.
TARGET="${TARGET/#\~/$HOME}"
if [ -L "$TARGET" ]; then
  TARGET="$(cd "$(dirname "$TARGET")" && cd "$(readlink "$TARGET")" 2>/dev/null && pwd || echo "$TARGET")"
fi

BACKUP_DIR="$(dirname "$TARGET")/.skill-backups"

SKILLS=()
for path in "$SRC_DIR"/*/; do
  [ -f "${path}SKILL.md" ] || continue
  SKILLS+=("$(basename "$path")")
done
[ ${#SKILLS[@]} -gt 0 ] || die "no skills with a SKILL.md found in $SRC_DIR"

if [ ${#SELECTED_SKILLS[@]} -gt 0 ]; then
  # Validate the entire selection before touching the target directory.
  for name in "${SELECTED_SKILLS[@]}"; do
    found=0
    for available in "${SKILLS[@]}"; do
      [ "$name" != "$available" ] || found=1
    done
    [ "$found" -eq 1 ] || die "unknown skill: $name (available: ${SKILLS[*]})"
  done
  SKILLS=()
  for name in "${SELECTED_SKILLS[@]}"; do
    case " ${SKILLS[*]:-} " in *" $name "*) continue ;; esac
    SKILLS+=("$name")
  done
  if [ "$UNINSTALL" -eq 0 ]; then
    case " ${SKILLS[*]} " in
      *" figma-full-cycle "*)
        for name in figma-feature-spec import-figma-assets figma-design-compare swiftui-adaptivity-check; do
          [ -f "$SRC_DIR/$name/SKILL.md" ] || die "required companion missing: $name"
          case " ${SKILLS[*]} " in *" $name "*) continue ;; esac
          SKILLS+=("$name")
        done
        ;;
    esac
  fi
fi

# Validate resource dependencies before installing any selected entry.
INSTALL_SHARED=0
if [ "$UNINSTALL" -eq 0 ]; then
  case " ${SKILLS[*]} " in
    *" figma-full-cycle "*|*" figma-design-compare "*|*" swiftui-adaptivity-check "*)
      INSTALL_SHARED=1
      for resource in scripts/screenshot_diff.py scripts/ui_guard.py scripts/localization_context.py \
        references/validation-context.md references/project-ui-conventions.md \
        references/layout-adaptivity-contract.md references/colors-contract.md \
        references/strings-workflow.md references/figma-mcp-acquisition.md; do
        [ -f "$SRC_DIR/$SHARED_NAME/$resource" ] || die "required shared resource missing: $SHARED_NAME/$resource"
        if [ "$FORCE" -eq 0 ] && { [ -e "$TARGET/$SHARED_NAME" ] || [ -L "$TARGET/$SHARED_NAME" ]; }; then
          [ -f "$TARGET/$SHARED_NAME/$resource" ] || die "installed shared resources are incomplete; re-run with --force: $TARGET/$SHARED_NAME/$resource"
        fi
      done
      ;;
  esac
fi

if [ "$UNINSTALL" -eq 1 ]; then
  for name in "${SKILLS[@]}"; do
    dest="$TARGET/$name"
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$SRC_DIR/$name" ]; then
      rm "$dest"
      log "removed symlink  $dest"
    elif [ -e "$dest" ]; then
      warn "$dest is not a symlink created by this script — left untouched, remove it yourself"
    else
      log "not installed    $dest"
    fi
  done
  exit 0
fi

mkdir -p "$TARGET"

# Resources are shared by consumers, so uninstall deliberately leaves them in place.
ENTRIES=("${SKILLS[@]}")
if [ "$INSTALL_SHARED" -eq 1 ]; then
  ENTRIES=("$SHARED_NAME" "${ENTRIES[@]}")
fi
for name in "${ENTRIES[@]}"; do
  src="$SRC_DIR/$name"
  dest="$TARGET/$name"

  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
    if [ "$MODE" = "copy" ]; then
      # This link is ours and contains no user data. Detach it from the checkout
      # when copy mode is requested, including a shared dependency installed earlier.
      rm "$dest"
      cp -R "$src" "$dest"
      log "copied           $dest (converted owned symlink)"
    else
      log "up to date       $dest"
    fi
    continue
  fi

  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ "$FORCE" -ne 1 ]; then
      warn "$dest already exists — skipped (re-run with --force to replace it)"
      continue
    fi
    # Back up outside the skills directory: an agent scanning it would otherwise
    # register the backup as a second, duplicate skill.
    mkdir -p "$BACKUP_DIR"
    backup="$BACKUP_DIR/$name.bak-$(date +%Y%m%d%H%M%S)"
    mv "$dest" "$backup"
    log "backed up        $backup"
  fi

  if [ "$MODE" = "copy" ]; then
    cp -R "$src" "$dest"
    log "copied           $dest"
  else
    ln -s "$src" "$dest"
    log "linked           $dest -> $src"
  fi
done

log ""
log "Done. Start a new agent session and check these skills: ${SKILLS[*]}"
