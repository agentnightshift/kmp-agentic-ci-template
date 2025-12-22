#!/bin/bash

# Branch Protection Setup Script
# This script configures branch protection rules for the 'main' branch
# using the GitHub CLI (gh).
#
# Prerequisites:
#   - GitHub CLI installed: https://cli.github.com/
#   - Authenticated with: gh auth login
#   - Requires 'repo' scope for private repos or 'public_repo' for public repos

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up branch protection for 'main' branch...${NC}"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed.${NC}"
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with GitHub CLI.${NC}"
    echo "Run: gh auth login"
    exit 1
fi

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null)

if [ -z "$REPO" ]; then
    echo -e "${RED}Error: Could not determine repository.${NC}"
    echo "Make sure you're in a Git repository connected to GitHub."
    exit 1
fi

echo -e "Repository: ${GREEN}$REPO${NC}"

# Configure branch protection using the GitHub API
echo -e "${YELLOW}Configuring branch protection rules...${NC}"

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "/repos/$REPO/branches/main/protection" \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["quality_gate", "ui_verification"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Branch protection configured successfully!${NC}"
    echo ""
    echo "Protection rules applied to 'main' branch:"
    echo "  • Require pull request before merging"
    echo "  • Require 1 approving review"
    echo "  • Dismiss stale approvals when new commits are pushed"
    echo "  • Require status checks to pass:"
    echo "    - quality_gate"
    echo "    - ui_verification"
    echo "  • Require branches to be up to date before merging"
    echo ""
    echo -e "${YELLOW}Note: Status checks will only appear after the first PR workflow run.${NC}"
else
    echo -e "${RED}✗ Failed to configure branch protection.${NC}"
    echo "Check your permissions and try again."
    exit 1
fi
