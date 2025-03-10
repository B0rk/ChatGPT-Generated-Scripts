#!/usr/bin/env bash

# Define color codes
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
NC="\e[0m" # No Color

TOOLS_DIR="$HOME/Tools"

# Ensure the directory exists
if [[ ! -d "$TOOLS_DIR" ]]; then
  echo -e "${RED}Directory $TOOLS_DIR does not exist. Exiting.${NC}"
  exit 1
fi

# Iterate over each subdirectory under ~/Tools
for repo in "$TOOLS_DIR"/*/; do
  # Skip if it’s not a directory (or if no directories exist)
  [[ -d "$repo" ]] || continue

  # Check if it’s a Git repository by looking for a .git folder
  if [[ -d "${repo}/.git" ]]; then
    echo -e "\nChecking repository: $repo"

    # Move into the repository directory
    cd "$repo" || {
      echo -e "${RED}Cannot enter directory $repo${NC}"
      continue
    }

    # Pull latest changes and capture output
    output=$(git pull 2>&1)
    exit_code=$?

    # Check for errors or conflicts
    if [[ $exit_code -ne 0 ]]; then
      echo -e "${RED}can not update${NC}"
      echo "Git output:"
      echo "$output"
    else
      # If there’s no error, check whether it was already up to date
      if echo "$output" | grep -q "Already up to date."; then
        echo -e "${GREEN}up to date${NC}"
      else
        # Repository has been updated
        echo -e "${YELLOW}updating needed/in progress${NC}"
      fi
    fi
  fi
done
