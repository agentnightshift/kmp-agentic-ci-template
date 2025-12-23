#!/bin/bash

# Setup Night Shift Agent Identity
# Usage: ./setup-agent-identity.sh [BOT_USERNAME] [BOT_EMAIL] [BOT_TOKEN]

set -e

# Source .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$BOT_NAME" ]; then
    BOT_NAME="Night Shift Agent"
fi

REPO_URL=$(git remote get-url origin)
# Extract clean repo URL (remove existing auth if any)
CLEAN_REPO_URL=$(echo "$REPO_URL" | sed -E 's/https:\/\/([^@]+@)?/https:\/\//')

echo "🤖 Configuring Git Identity for: $BOT_NAME"

# Check for required environment variables
if [ -z "$BOT_EMAIL" ]; then
    echo "❌ Error: BOT_EMAIL is not set in environment or .env file."
    exit 1
fi

# 1. Configure Commit Identity (Author)
echo "----------------------------------------"
echo "Step 1: Setting Commit Author..."

git config user.name "$BOT_NAME"
git config user.email "$BOT_EMAIL"

echo "✓ Local user.name set to: '$BOT_NAME'"
echo "✓ Local user.email set to: '$BOT_EMAIL'"

# 2. Configure Authentication (Pusher)
echo "----------------------------------------"
echo "Step 2: Configuring Push Authentication..."

if [ -n "$GH_BOT_TOKEN" ] && [ -n "$BOT_USERNAME" ]; then
    # Construct Authenticated URL
    # Format: https://USERNAME:TOKEN@github.com/OWNER/REPO.git
    AUTH_URL=$(echo "$CLEAN_REPO_URL" | sed -E "s/https:\/\//https:\/\/${BOT_USERNAME}:${GH_BOT_TOKEN}@/")
    
    git remote set-url origin "$AUTH_URL"
    
    echo "✓ Remote 'origin' updated with bot credentials for user '$BOT_USERNAME'."
else
    echo "ℹ️  GH_BOT_TOKEN or BOT_USERNAME not found. Skipping authentication setup."
    echo "   (You will push using your existing credentials, but commits will be authored by '$BOT_NAME')"
fi

echo "----------------------------------------"
echo "✅ Configuration Complete!"
