#!/usr/bin/env bash
set -uo pipefail

# Define color codes (using \033 for portability)
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
NC="\033[0m"

TOOLS_DIR="$HOME/Tools"

# Counters for summary
count_updated=0
count_uptodate=0
count_failed=0
count_skipped=0

# Ensure the directory exists
if [[ ! -d "$TOOLS_DIR" ]]; then
  echo -e "${RED}Directory $TOOLS_DIR does not exist. Exiting.${NC}" >&2
  exit 1
fi

# Iterate over each subdirectory under ~/Tools
for repo in "$TOOLS_DIR"/*/; do
  # Skip if it's not a directory (or if no directories exist)
  [[ -d "$repo" ]] || continue

  # Check if it's a Git repository by looking for a .git folder
  if [[ -d "${repo}.git" ]]; then
    repo_name="${repo%/}"
    repo_name="${repo_name##*/}"
    echo -e "\nChecking repository: ${repo_name}"

    # Use git -C to avoid changing the working directory
    output=$(git -C "$repo" pull --ff-only 2>&1)
    exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
      echo -e "${RED}failed to update${NC}"
      echo "$output" >&2
      ((count_failed++))
    elif [[ "$output" == *"Already up to date."* ]]; then
      echo -e "${GREEN}up to date${NC}"
      ((count_uptodate++))
    else
      echo -e "${YELLOW}updated${NC}"
      ((count_updated++))
    fi
  else
    ((count_skipped++))
  fi
done

# Print summary
echo -e "\n--- Summary ---"
echo -e "${GREEN}Up to date: ${count_uptodate}${NC}"
echo -e "${YELLOW}Updated:    ${count_updated}${NC}"
echo -e "${RED}Failed:     ${count_failed}${NC}"
echo "Skipped (not git repos): ${count_skipped}"

# Exit with error if any repos failed
if [[ $count_failed -gt 0 ]]; then
  exit 1
fi
