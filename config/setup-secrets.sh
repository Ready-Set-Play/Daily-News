#!/usr/bin/env bash
#
# config/setup-secrets.sh
# Securely encodes and stores Daily News Digest config files as GitHub Secrets.
# Run once after forking, then re-run any time you edit your config files.
#
# Requirements: gh CLI (https://cli.github.com/), python3, base64 (standard)

set -euo pipefail

# ---------------------------------------------------------------------------
# Global temp-file registry + EXIT trap
# Covers all mktemp calls even when set -e aborts mid-function,
# where RETURN traps would not fire.
# ---------------------------------------------------------------------------
_TMPFILES=()
_cleanup() { [[ ${#_TMPFILES[@]} -gt 0 ]] && rm -f "${_TMPFILES[@]}" 2>/dev/null; true; }
trap _cleanup EXIT

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
info() { printf "  %s\n"       "$1"; }
ok()   { printf "  [OK] %s\n"  "$1"; }
warn() { printf "  [WARN] %s\n" "$1" >&2; }
die()  { printf "\n  [ERROR] %s\n\n" "$1" >&2; exit 1; }

# ---------------------------------------------------------------------------
# OS-portable base64 with line-wrap suppressed
# macOS (BSD): base64 -b0    Linux (GNU): base64 -w0
# ---------------------------------------------------------------------------
b64_encode() {
    case "$(uname -s)" in
        Darwin) base64 -b0 -i "$1" ;;
        *)      base64 -w0 "$1"    ;;
    esac
}

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
check_deps() {
    info "Checking required tools..."
    command -v gh      &>/dev/null || die "'gh' not found. Install the GitHub CLI and run 'gh auth login'. See: https://cli.github.com/"
    command -v base64  &>/dev/null || die "'base64' not found. This is a standard system utility."
    command -v python3 &>/dev/null || die "'python3' not found. Python 3 is required for YAML validation."
    ok "All tools found."
}

check_auth() {
    info "Checking GitHub authentication..."
    gh auth status &>/dev/null || die "Not logged in to the GitHub CLI. Run 'gh auth login' and try again."
    ok "Authenticated with GitHub."
}

# ---------------------------------------------------------------------------
# P0: Git history audit
# Hard-fail if personal config files appear in any prior commit.
# .gitignore prevents future commits but does NOT erase history.
# ---------------------------------------------------------------------------
check_git_history() {
    info "Auditing git history for committed config files..."
    local found=0
    for f in config/sources.yaml config/topics.yaml feedback/wrangler.toml feedback/history.jsonl; do
        if git log --all --full-history -- "$f" 2>/dev/null | grep -q "^commit"; then
            warn "'$f' appears in git history."
            found=1
        fi
    done

    if [[ "$found" -eq 1 ]]; then
        cat >&2 <<'MSG'

  [ERROR] One or more personal config files were found in git history.
  Adding them to .gitignore prevents future commits but does NOT remove
  the data from existing commits. Anyone with repo access can recover it.

  Before making this repository public, rewrite history with git-filter-repo:

    pip install git-filter-repo
    git filter-repo --path config/sources.yaml --invert-paths
    git filter-repo --path config/topics.yaml --invert-paths
    git push --force origin main

  WARNING: Force-pushing rewrites public history. Coordinate with any
  collaborators before doing this.

  After rewriting history, re-run this script.

MSG
        exit 1
    fi
    ok "No config files found in git history."
}

# ---------------------------------------------------------------------------
# YAML validation: parse and assert expected root key is present and non-null
# ---------------------------------------------------------------------------
validate_yaml() {
    local file="$1"
    local root_key="$2"
    if ! python3 -c "
import sys, yaml
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f)
if not isinstance(data, dict) or sys.argv[2] not in data:
    print(f\"ERROR: '{sys.argv[1]}' must be a YAML mapping with a top-level '{sys.argv[2]}' key.\", file=sys.stderr)
    sys.exit(1)
" "$file" "$root_key" 2>&1; then
        die "YAML validation failed for '$file'. Fix the syntax errors shown above and try again."
    fi
    ok "'$file' is valid YAML with a '$root_key' root key."
}

# ---------------------------------------------------------------------------
# Idempotency: probe secret existence via gh secret list (gh secret get
# is not a valid subcommand in gh CLI v2.x)
# ---------------------------------------------------------------------------
secret_exists() {
    gh secret list --repo "$1" --json name -q '.[].name' 2>/dev/null \
        | grep -qx "$2"
}

# ---------------------------------------------------------------------------
# Encode a config file and store it as a GitHub Secret.
# Uses mktemp + trap to avoid base64 content appearing in shell history.
# ---------------------------------------------------------------------------
set_config_secret() {
    local file="$1"
    local secret_name="$2"
    local repo="$3"
    local root_key="$4"
    local example="${file}.example"
    local tmp

    # Copy from .example template if the real file doesn't exist
    if [[ ! -f "$file" ]]; then
        if [[ -f "$example" ]]; then
            printf "\n  '%s' not found.\n" "$file"
            read -r -p "  Copy from '$example' and edit now? (Y/n): " copy_confirm
            [[ "$copy_confirm" == "n" || "$copy_confirm" == "N" ]] && die "Please create '$file' before running this script."
            cp "$example" "$file"
            info "Copied '$example' to '$file'. Open it in your editor, fill in your preferences, then press Enter."
            read -r -p "  Press Enter when done editing... "
        else
            die "'$file' not found and no '$example' template exists. Cannot continue."
        fi
    fi

    validate_yaml "$file" "$root_key"

    if secret_exists "$repo" "$secret_name"; then
        printf "\n  Secret '%s' already exists in %s.\n" "$secret_name" "$repo"
        read -r -p "  Overwrite it? (y/N): " overwrite_confirm
        [[ "$overwrite_confirm" == "y" || "$overwrite_confirm" == "Y" ]] || { info "Skipping '$secret_name'."; return; }
    fi

    info "Encoding '$file' and uploading to GitHub Secrets..."
    tmp=$(mktemp)
    _TMPFILES+=("$tmp")
    b64_encode "$file" > "$tmp"
    gh secret set "$secret_name" --repo "$repo" --body "$tmp"
    ok "Secret '$secret_name' set in $repo."
}

# ---------------------------------------------------------------------------
# NYT API key — stored via temp file to avoid shell history exposure
# ---------------------------------------------------------------------------
set_nyt_secret() {
    local repo="$1"
    local tmp

    printf "\n  The NYT source plugin requires an 'NYT_API_KEY' secret.\n"
    read -r -p "  Set NYT_API_KEY now? (y/N): " nyt_confirm
    [[ "$nyt_confirm" == "y" || "$nyt_confirm" == "Y" ]] || return

    read -r -s -p "  Enter your New York Times API Key: " nyt_key
    echo
    [[ -n "$nyt_key" ]] || die "API key cannot be empty."

    tmp=$(mktemp)
    _TMPFILES+=("$tmp")
    printf '%s' "$nyt_key" > "$tmp"
    gh secret set "NYT_API_KEY" --repo "$repo" --body "$tmp"
    ok "Secret 'NYT_API_KEY' set in $repo."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."   # ensure we run from the repo root

printf "\n  Daily News Digest — Secure Config Setup\n"
printf "  ==========================================\n\n"

check_deps
check_auth
check_git_history

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null) \
    || die "Could not detect the GitHub repo. Run this script from inside the cloned repository."
info "Target repo: $REPO"
echo

set_config_secret "config/sources.yaml" "CONFIG_SOURCES_B64" "$REPO" "sources"
echo
set_config_secret "config/topics.yaml"  "CONFIG_TOPICS_B64"  "$REPO" "sections"
echo
set_nyt_secret "$REPO"

printf "\n  Setup complete. Trigger a manual run from the Actions tab to verify.\n"
printf "  To update your config later, just edit the YAML files and re-run this script.\n\n"
