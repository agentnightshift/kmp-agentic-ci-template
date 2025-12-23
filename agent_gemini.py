#!/usr/bin/env python3
"""
🌙 Night Shift Agent v3.0 - Autonomous Coding Assistant
========================================================
An AI-powered agent that processes tasks, creates PRs, and monitors CI.

Workflow:
1. Process all tasks from tasks.txt
2. Create a feature branch and push to fork
3. Create a Pull Request from fork to upstream
4. Monitor CI status and fix any failures
5. Loop until CI passes or max retries exceeded

Features:
- Build verification before task completion
- Fork + PR workflow for safe collaboration
- CI monitoring with automatic fixes
- Retry logic with exponential backoff
- Structured logging
"""

import os
import subprocess
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("AGENT_MODEL", "x-ai/grok-4.1-fast:free")
GH_BOT_TOKEN = os.getenv("GH_BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "agentnightshift")

# Agent behavior settings
MAX_ITERATIONS = 50          # Maximum tool calls per task
MAX_RETRIES = 3              # API retry attempts
MAX_CI_FIX_ATTEMPTS = 5      # Maximum attempts to fix CI failures
RETRY_BASE_DELAY = 2         # Base delay for exponential backoff (seconds)
CI_POLL_INTERVAL = 60        # Seconds between CI status checks
MAX_FILES_IN_CONTEXT = 100   # Limit files listed in context
REQUIRE_BUILD_VERIFICATION = True  # Require passing build before marking done

# Branch naming
BRANCH_PREFIX = "nightshift"

# Logging setup
LOG_DIR = Path(".agent_logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NightShiftAgent")

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

# =============================================================================
# BUILD VERIFICATION STATE
# =============================================================================

class BuildState:
    """Tracks build and test verification status."""
    def __init__(self):
        self.build_attempted = False
        self.build_passed = False
        self.test_attempted = False
        self.test_passed = False
        self.last_error = None

    def reset(self):
        self.__init__()

    def is_verified(self) -> bool:
        """Returns True if build has been verified as passing."""
        if not REQUIRE_BUILD_VERIFICATION:
            return True
        return self.build_attempted and self.build_passed

    def __str__(self):
        return (f"BuildState(build={'✅' if self.build_passed else '❌'}, "
                f"test={'✅' if self.test_passed else '❌'})")

build_state = BuildState()

# =============================================================================
# TOOLS
# =============================================================================

def read_file(path: str) -> str:
    """Reads a file from the filesystem."""
    try:
        with open(path, "r") as f:
            content = f.read()
        logger.info(f"📖 Read file: {path} ({len(content)} bytes)")
        return content
    except Exception as e:
        logger.error(f"❌ Failed to read {path}: {e}")
        return f"Error reading file {path}: {e}"


def write_file(path: str, content: str) -> str:
    """Writes content to a file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        logger.info(f"✍️ Wrote file: {path} ({len(content)} bytes)")

        # Reset build state since code changed
        build_state.build_passed = False
        build_state.build_attempted = False

        return f"Successfully wrote to {path}"
    except Exception as e:
        logger.error(f"❌ Failed to write {path}: {e}")
        return f"Error writing to file {path}: {e}"


def list_files(path: str = ".") -> str:
    """Lists files in the project (with smart filtering and limits)."""
    files = []
    ignore_dirs = {".git", ".gradle", ".idea", ".venv", "__pycache__", "build", ".kotlin", "node_modules"}
    ignore_extensions = {".jar", ".class", ".pyc", ".so", ".dylib"}

    logger.info(f"📂 Listing files in: {path}")

    for root, dirs, filenames in os.walk(path):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]

        for filename in filenames:
            if filename.startswith("."):
                continue
            if any(filename.endswith(ext) for ext in ignore_extensions):
                continue

            files.append(os.path.join(root, filename))

            if len(files) >= MAX_FILES_IN_CONTEXT:
                logger.warning(f"⚠️ File list truncated at {MAX_FILES_IN_CONTEXT} files")
                files.append(f"... (truncated, {MAX_FILES_IN_CONTEXT}+ files)")
                return "\n".join(files)

    return "\n".join(files)


def run_shell(command: str) -> str:
    """Executes a shell command and tracks build verification status."""
    global build_state

    logger.info(f"🤖 Executing: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        output = result.stdout + result.stderr

        # Track build/test status
        is_build_command = any(kw in command.lower() for kw in
            ["gradlew", "gradle", "build", "compile", "assemble"])
        is_test_command = any(kw in command.lower() for kw in
            ["test", "check", "verify"])

        if is_build_command or is_test_command:
            build_state.build_attempted = True
            if result.returncode == 0:
                build_state.build_passed = True
                if is_test_command:
                    build_state.test_attempted = True
                    build_state.test_passed = True
                logger.info("✅ Command succeeded (exit code 0)")
            else:
                build_state.build_passed = False
                build_state.last_error = output[-2000:]  # Keep last 2KB of error
                logger.warning(f"⚠️ Command failed (exit code {result.returncode})")

        if result.returncode != 0:
            return f"Command failed with exit code {result.returncode}:\n{output}"

        return output

    except subprocess.TimeoutExpired:
        logger.error(f"❌ Command timed out: {command}")
        return "Error: Command timed out after 600 seconds"
    except Exception as e:
        logger.error(f"❌ Command error: {e}")
        return f"Error executing command: {e}"


# Tool definitions for OpenAI API
tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the file to read"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. WARNING: After writing, you MUST run the build to verify the code compiles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the file to write"},
                    "content": {"type": "string", "description": "The content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files in a directory (recursive, filtered)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The directory to list (default .)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command. Use this to run builds (./gradlew build) and tests (./gradlew test).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to run"}
                },
                "required": ["command"]
            }
        }
    }
]

available_functions = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "run_shell": run_shell,
}

# =============================================================================
# API CALL WITH RETRY
# =============================================================================

def call_api_with_retry(messages: list, tools_list: list) -> object:
    """Call the API with exponential backoff retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=tools_list,
            )
            return response
        except Exception as e:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(f"⚠️ API error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

            if attempt < MAX_RETRIES - 1:
                logger.info(f"⏳ Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"❌ API failed after {MAX_RETRIES} attempts")
                raise


# =============================================================================
# GIT & GITHUB HELPERS
# =============================================================================

def run_cmd(command: str, timeout: int = 120, use_bot_token: bool = True) -> tuple[bool, str]:
    """Run a shell command and return (success, output).
    
    If use_bot_token is True and GH_BOT_TOKEN is set, gh commands will use
    the bot's token instead of the logged-in user's token.
    """
    try:
        # Set up environment with bot token for gh commands
        env = os.environ.copy()
        if use_bot_token and GH_BOT_TOKEN and command.strip().startswith("gh "):
            env["GITHUB_TOKEN"] = GH_BOT_TOKEN
            env["GH_TOKEN"] = GH_BOT_TOKEN
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except Exception as e:
        return False, str(e)


def get_repo_info() -> dict:
    """Get information about the current repository."""
    success, output = run_cmd("gh repo view --json nameWithOwner,url")
    if success:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass
    return {}


def get_current_branch() -> str:
    """Get the current git branch name."""
    success, output = run_cmd("git branch --show-current")
    return output if success else "main"


def setup_fork() -> tuple[bool, str]:
    """
    Ensure the bot has a fork of the repository and set up remotes.
    Returns (success, fork_remote_name).
    """
    logger.info("🍴 Setting up fork...")

    # Get the upstream repo info
    repo_info = get_repo_info()
    upstream_repo = repo_info.get("nameWithOwner", "")

    if not upstream_repo:
        logger.error("❌ Could not determine upstream repository")
        return False, ""

    logger.info(f"📦 Upstream repo: {upstream_repo}")

    # Check if we already have a 'fork' remote
    success, remotes = run_cmd("git remote -v")
    if "fork" in remotes:
        logger.info("✅ Fork remote already exists")
        return True, "fork"

    # Try to create/get the fork using gh
    logger.info("🍴 Creating fork (if not exists)...")
    success, output = run_cmd(f"gh repo fork {upstream_repo} --clone=false --remote=false")

    if not success and "already exists" not in output.lower():
        logger.warning(f"⚠️ Fork command output: {output}")

    # Get the fork URL
    owner = upstream_repo.split("/")[0]
    repo_name = upstream_repo.split("/")[1]
    fork_repo = f"{BOT_USERNAME}/{repo_name}"

    # Add fork as remote
    if GH_BOT_TOKEN:
        fork_url = f"https://{BOT_USERNAME}:{GH_BOT_TOKEN}@github.com/{fork_repo}.git"
    else:
        fork_url = f"https://github.com/{fork_repo}.git"

    success, output = run_cmd(f'git remote add fork "{fork_url}"')
    if not success and "already exists" not in output:
        logger.error(f"❌ Failed to add fork remote: {output}")
        return False, ""

    logger.info(f"✅ Fork remote configured: {fork_repo}")
    return True, "fork"


def create_feature_branch() -> str:
    """Create and checkout a new feature branch."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"{BRANCH_PREFIX}/{timestamp}"

    logger.info(f"🌿 Creating feature branch: {branch_name}")

    # Ensure we're on main first and up to date
    run_cmd("git checkout main")
    run_cmd("git fetch origin")
    run_cmd("git reset --hard origin/main")

    # Create and checkout new branch
    success, output = run_cmd(f"git checkout -b {branch_name}")
    if success:
        logger.info(f"✅ Created branch: {branch_name}")
    else:
        logger.error(f"❌ Failed to create branch: {output}")

    return branch_name


def push_to_fork(branch_name: str, remote: str = "fork") -> bool:
    """Push the current branch to the fork."""
    logger.info(f"📤 Pushing branch to {remote}: {branch_name}")

    success, output = run_cmd(f"git push -u {remote} {branch_name} --force")
    if success:
        logger.info("✅ Pushed branch successfully")
    else:
        logger.error(f"❌ Push failed: {output}")

    return success


def create_pull_request(branch_name: str, title: str, body: str) -> tuple[bool, str]:
    """Create a Pull Request from fork to upstream and return (success, pr_url)."""
    logger.info("📝 Creating Pull Request from fork to upstream...")

    # Get upstream repo info
    repo_info = get_repo_info()
    upstream_repo = repo_info.get("nameWithOwner", "")

    if not upstream_repo:
        return False, "Could not determine upstream repository"

    # Create PR from fork
    # Format: gh pr create --repo UPSTREAM --head BOT_USER:branch
    head_ref = f"{BOT_USERNAME}:{branch_name}"

    # Escape quotes in title and body for shell
    safe_title = title.replace('"', '\\"').replace("'", "\\'")
    safe_body = body.replace('"', '\\"').replace("'", "\\'")

    cmd = f'gh pr create --repo {upstream_repo} --head "{head_ref}" --title "{safe_title}" --body "{safe_body}"'
    success, output = run_cmd(cmd, timeout=60)

    if success:
        # Extract PR URL from output (usually the last line)
        pr_url = output.strip().split('\n')[-1]
        logger.info(f"✅ Created PR: {pr_url}")
        return True, pr_url
    else:
        logger.error(f"❌ Failed to create PR: {output}")
        return False, output


def get_pr_number_from_branch(branch_name: str) -> str:
    """Get the PR number for a branch."""
    repo_info = get_repo_info()
    upstream_repo = repo_info.get("nameWithOwner", "")
    head_ref = f"{BOT_USERNAME}:{branch_name}"

    success, output = run_cmd(f'gh pr list --repo {upstream_repo} --head "{head_ref}" --json number --jq ".[0].number"')
    return output.strip() if success else ""


def get_pr_status(branch_name: str) -> dict:
    """Get the CI/checks status of a PR."""
    logger.info(f"🔍 Checking PR status for branch: {branch_name}")

    pr_number = get_pr_number_from_branch(branch_name)
    if not pr_number:
        return {"success": False, "error": "Could not find PR number"}

    repo_info = get_repo_info()
    upstream_repo = repo_info.get("nameWithOwner", "")

    success, output = run_cmd(f'gh pr checks {pr_number} --repo {upstream_repo} --json name,state,conclusion')

    if success:
        try:
            checks = json.loads(output)
            return {
                "success": True,
                "checks": checks,
                "all_passed": all(c.get("conclusion") == "success" for c in checks if c.get("state") == "completed"),
                "any_failed": any(c.get("conclusion") == "failure" for c in checks),
                "pending": any(c.get("state") in ["pending", "queued", "in_progress"] for c in checks)
            }
        except json.JSONDecodeError:
            return {"success": False, "error": "Failed to parse checks JSON", "raw": output}
    else:
        return {"success": False, "error": output}


def get_pr_check_logs(branch_name: str) -> str:
    """Get information about failed CI checks."""
    logger.info("📋 Fetching failed check info...")

    pr_number = get_pr_number_from_branch(branch_name)
    if not pr_number:
        return "Could not find PR number"

    repo_info = get_repo_info()
    upstream_repo = repo_info.get("nameWithOwner", "")

    success, output = run_cmd(f'gh pr checks {pr_number} --repo {upstream_repo} --json name,conclusion,detailsUrl')

    if not success:
        return f"Failed to get checks: {output}"

    try:
        checks = json.loads(output)
        failed_checks = [c for c in checks if c.get("conclusion") == "failure"]

        if not failed_checks:
            return "No failed checks found."

        logs = ["Failed CI checks:"]
        for check in failed_checks:
            logs.append(f"- {check.get('name')}: {check.get('detailsUrl', 'No URL')}")

        return "\n".join(logs)
    except json.JSONDecodeError:
        return f"Failed to parse checks: {output}"


# =============================================================================
# TASK PROCESSING
# =============================================================================

def process_task(task: str, architecture_guide: str, project_files: str) -> bool:
    """
    Process a single task. Returns True if task completed successfully with verified build.
    """
    global build_state
    build_state.reset()

    system_prompt = f"""You are the Night Shift Agent, an autonomous coding assistant for a Kotlin Multiplatform project.

ARCHITECTURE GUIDE:
{architecture_guide}

PROJECT FILES:
{project_files}

INSTRUCTIONS:
1. Analyze the task carefully.
2. Read necessary files to understand the existing code.
3. Modify or create files using 'write_file'.
4. **CRITICAL**: After ANY code changes, you MUST run './gradlew build' to verify compilation.
5. If the build fails, analyze the error and fix the code. Repeat until build passes.
6. Run tests with './gradlew test' if appropriate.
7. Once build passes, commit your changes with a descriptive message using run_shell with 'git add . && git commit -m "message"'.

GUARDRAILS:
- NEVER claim a task is complete if the build has not been verified.
- If you modify code, you MUST run the build before finishing.
- If the build fails, you MUST attempt to fix it.
- Be concise in your reasoning.

When you have completed the task with a PASSING build and committed, provide a summary of what you did."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"TASK: {task}"}
    ]

    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1
        logger.info(f"🔄 Iteration {iteration}/{MAX_ITERATIONS}")

        try:
            response = call_api_with_retry(messages, tools)
        except Exception as e:
            logger.error(f"❌ Failed to get response: {e}")
            return False

        response_message = response.choices[0].message
        messages.append(response_message)

        tool_calls = response_message.tool_calls

        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions.get(function_name)

                if not function_to_call:
                    logger.error(f"❌ Unknown function: {function_name}")
                    continue

                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse arguments: {e}")
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Error: Invalid JSON arguments: {e}",
                    })
                    continue

                # Execute tool
                function_response = function_to_call(**function_args)

                # Truncate very long responses to save context
                if len(function_response) > 10000:
                    function_response = function_response[:5000] + "\n\n... [truncated] ...\n\n" + function_response[-5000:]

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                })
        else:
            # No more tool calls - agent wants to finish
            logger.info(f"\n🧠 Agent Report:\n{response_message.content}")

            # Check if build was verified
            if build_state.is_verified():
                logger.info(f"✅ Build verified: {build_state}")
                return True
            else:
                logger.warning(f"⚠️ Build NOT verified: {build_state}")

                if REQUIRE_BUILD_VERIFICATION:
                    messages.append({
                        "role": "user",
                        "content": (
                            "SYSTEM: Build has NOT been verified. "
                            "You MUST run './gradlew build' to verify your changes compile. "
                            "Do not finish until the build passes."
                        )
                    })
                    continue
                else:
                    return True

    logger.error(f"❌ Task exceeded max iterations ({MAX_ITERATIONS})")
    return False


def fix_ci_failure(branch_name: str, architecture_guide: str, project_files: str) -> bool:
    """
    Attempt to fix CI failures by analyzing logs and making corrections.
    """
    global build_state
    build_state.reset()

    check_logs = get_pr_check_logs(branch_name)

    logger.info("🔧 Attempting to fix CI failure...")
    logger.info(f"CI Failure Info:\n{check_logs}")

    system_prompt = f"""You are the Night Shift Agent, an autonomous coding assistant for a Kotlin Multiplatform project.

ARCHITECTURE GUIDE:
{architecture_guide}

PROJECT FILES:
{project_files}

CI FAILURE INFORMATION:
{check_logs}

YOUR TASK:
The CI pipeline has failed. You need to:
1. Analyze the CI failure information above.
2. Read the relevant files to understand the issue.
3. Fix the code that is causing the CI failure.
4. Run './gradlew build' locally to verify your fix works.
5. Commit your changes with 'git add . && git commit -m "fix: description"'.

Common CI failures include:
- Compilation errors
- Test failures  
- Detekt/lint issues
- Missing dependencies

Be thorough and fix ALL issues."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Please fix the CI failures described above."}
    ]

    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1
        logger.info(f"🔄 CI Fix Iteration {iteration}/{MAX_ITERATIONS}")

        try:
            response = call_api_with_retry(messages, tools)
        except Exception as e:
            logger.error(f"❌ Failed to get response: {e}")
            return False

        response_message = response.choices[0].message
        messages.append(response_message)

        tool_calls = response_message.tool_calls

        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions.get(function_name)

                if not function_to_call:
                    continue

                try:
                    function_args = json.loads(tool_call.function.arguments)
                    function_response = function_to_call(**function_args)

                    if len(function_response) > 10000:
                        function_response = function_response[:5000] + "\n\n... [truncated] ...\n\n" + function_response[-5000:]

                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(function_response),
                    })
                except Exception as e:
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Error: {e}",
                    })
        else:
            logger.info(f"\n🧠 CI Fix Report:\n{response_message.content}")

            if build_state.is_verified():
                return True
            else:
                messages.append({
                    "role": "user",
                    "content": "SYSTEM: Build NOT verified. Run './gradlew build' now."
                })
                continue

    return False


# =============================================================================
# MAIN WORKFLOW
# =============================================================================

def main():
    """Main entry point for the Night Shift Agent."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  🌙 Night Shift Agent v3.0                                   ║
    ║  Autonomous Coding Assistant with Fork + PR Workflow         ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    logger.info("🚀 Starting Night Shift Agent")
    logger.info(f"📝 Log file: {LOG_FILE}")
    logger.info(f"🤖 Model: {MODEL_NAME}")
    logger.info(f"� Bot username: {BOT_USERNAME}")
    logger.info(f"�🔧 Max iterations per task: {MAX_ITERATIONS}")
    logger.info(f"🔒 Build verification: {'REQUIRED' if REQUIRE_BUILD_VERIFICATION else 'OPTIONAL'}")

    if not API_KEY:
        logger.error("❌ OPENROUTER_API_KEY not set in environment")
        sys.exit(1)

    # Load architecture guide
    architecture_guide = ""
    if os.path.exists("ARCHITECTURE.md"):
        architecture_guide = read_file("ARCHITECTURE.md")

    # Load project file list
    project_files = list_files()

    # Check for task queue
    if not os.path.exists("tasks.txt"):
        logger.warning("⚠️ No tasks.txt found")
        print("\nCreate a tasks.txt file with one task per line.")
        return

    # =========================================================================
    # PHASE 0: Setup Fork
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("🍴 PHASE 0: Setting Up Fork")
    logger.info("="*60)

    fork_success, fork_remote = setup_fork()
    if not fork_success:
        logger.error("❌ Failed to set up fork. Exiting.")
        sys.exit(1)

    # =========================================================================
    # PHASE 1: Process all tasks
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("📋 PHASE 1: Processing Tasks")
    logger.info("="*60)

    # Create feature branch for this session
    original_branch = get_current_branch()
    feature_branch = create_feature_branch()

    with open("tasks.txt", "r") as f:
        lines = f.readlines()

    tasks_processed = 0
    tasks_succeeded = 0
    completed_tasks = []

    while True:
        with open("tasks.txt", "r") as f:
            lines = f.readlines()

        # Find first unchecked task
        task_index = -1
        current_task = ""
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("[x]") and not stripped.startswith("[!]") and not stripped.startswith("#"):
                task_index = i
                current_task = stripped
                break

        if task_index == -1:
            logger.info("✅ All tasks completed!")
            break

        logger.info(f"\n{'='*60}")
        logger.info(f"▶️ Processing Task {task_index + 1}: {current_task}")
        logger.info(f"{'='*60}")

        tasks_processed += 1

        success = process_task(current_task, architecture_guide, project_files)

        if success:
            lines[task_index] = f"[x] {lines[task_index].lstrip()}"
            with open("tasks.txt", "w") as f:
                f.writelines(lines)
            logger.info(f"✅ Marked task as done: {current_task}")
            tasks_succeeded += 1
            completed_tasks.append(current_task)
        else:
            logger.error(f"❌ Task failed (not marked as done): {current_task}")
            lines[task_index] = f"[!] {lines[task_index].lstrip()}"
            with open("tasks.txt", "w") as f:
                f.writelines(lines)
            logger.info("⏭️ Skipping to next task...")

        time.sleep(2)

    # =========================================================================
    # PHASE 2: Create Pull Request
    # =========================================================================
    if tasks_succeeded == 0:
        logger.warning("⚠️ No tasks completed successfully. Skipping PR creation.")
        run_cmd(f"git checkout {original_branch}")
        return

    logger.info("\n" + "="*60)
    logger.info("📤 PHASE 2: Creating Pull Request")
    logger.info("="*60)

    # Push to fork
    if not push_to_fork(feature_branch, fork_remote):
        logger.error("❌ Failed to push to fork. Cannot create PR.")
        return

    # Create PR
    pr_title = f"🌙 Night Shift: {tasks_succeeded} task(s) completed"
    pr_body = f"""## 🌙 Night Shift Agent Report

**Session**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Tasks Completed**: {tasks_succeeded}/{tasks_processed}

### Completed Tasks:
{chr(10).join(f'- [x] {task}' for task in completed_tasks)}

### Log File:
`{LOG_FILE}`

---
*This PR was automatically created by the Night Shift Agent.*
"""

    pr_success, pr_url = create_pull_request(feature_branch, pr_title, pr_body)

    if not pr_success:
        logger.error(f"❌ Failed to create PR: {pr_url}")
        return

    logger.info(f"✅ PR Created: {pr_url}")

    # =========================================================================
    # PHASE 3: Monitor CI and Fix Failures
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("🔍 PHASE 3: Monitoring CI Status")
    logger.info("="*60)

    ci_fix_attempts = 0

    while ci_fix_attempts < MAX_CI_FIX_ATTEMPTS:
        logger.info(f"⏳ Waiting {CI_POLL_INTERVAL}s for CI to run...")
        time.sleep(CI_POLL_INTERVAL)

        status = get_pr_status(feature_branch)

        if not status.get("success"):
            logger.warning(f"⚠️ Could not get PR status: {status.get('error')}")
            continue

        if status.get("pending"):
            logger.info("⏳ CI still running...")
            continue

        if status.get("all_passed"):
            logger.info("🎉 All CI checks passed!")
            break

        if status.get("any_failed"):
            ci_fix_attempts += 1
            logger.warning(f"❌ CI failed! Attempting fix {ci_fix_attempts}/{MAX_CI_FIX_ATTEMPTS}")

            fix_success = fix_ci_failure(feature_branch, architecture_guide, project_files)

            if fix_success:
                # Push the fix to fork
                push_to_fork(feature_branch, fork_remote)
                logger.info("📤 Pushed CI fix. Waiting for new CI run...")
            else:
                logger.error("❌ Failed to fix CI issues")

    # =========================================================================
    # Summary
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("📊 Session Summary")
    logger.info("="*60)
    logger.info(f"   Tasks processed: {tasks_processed}")
    logger.info(f"   Tasks succeeded: {tasks_succeeded}")
    logger.info(f"   Tasks failed:    {tasks_processed - tasks_succeeded}")
    logger.info(f"   CI fix attempts: {ci_fix_attempts}")
    logger.info(f"   PR URL:          {pr_url}")
    logger.info(f"   Log file:        {LOG_FILE}")
    logger.info("\n🌙 Night Shift Agent signing off. Good night!")


if __name__ == "__main__":
    main()
