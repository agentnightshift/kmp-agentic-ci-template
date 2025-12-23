#!/usr/bin/env python3
"""
🌙 Night Shift Agent - Autonomous Coding Assistant
==================================================
An AI-powered agent that processes tasks from a queue, modifies code,
and verifies builds before marking tasks complete.

Features:
- Build verification before task completion
- Retry logic with exponential backoff
- Max iteration guards
- Structured logging
- Context-aware file listing
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

# Agent behavior settings
MAX_ITERATIONS = 50          # Maximum tool calls per task
MAX_RETRIES = 3              # API retry attempts
RETRY_BASE_DELAY = 2         # Base delay for exponential backoff (seconds)
MAX_FILES_IN_CONTEXT = 100   # Limit files listed in context
REQUIRE_BUILD_VERIFICATION = True  # Require passing build before marking done

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
                logger.info(f"✅ Command succeeded (exit code 0)")
            else:
                build_state.build_passed = False
                build_state.last_error = output[-2000:]  # Keep last 2KB of error
                logger.warning(f"⚠️ Command failed (exit code {result.returncode})")
        
        if result.returncode != 0:
            return f"Command failed with exit code {result.returncode}:\n{output}"
        
        return output
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Command timed out: {command}")
        return f"Error: Command timed out after 600 seconds"
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

def call_api_with_retry(messages: list, tools: list) -> object:
    """Call the API with exponential backoff retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=tools,
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
# MAIN AGENT LOOP
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
7. Once build passes, commit your changes with a descriptive message.

GUARDRAILS:
- NEVER claim a task is complete if the build has not been verified.
- If you modify code, you MUST run the build before finishing.
- If the build fails, you MUST attempt to fix it.
- Be concise in your reasoning.

When you have completed the task with a PASSING build, provide a summary of what you did."""

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
                    function_response = f"Error: Invalid JSON arguments: {e}"
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
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
                    # Push the agent to verify the build
                    messages.append({
                        "role": "user",
                        "content": (
                            "SYSTEM: Build has NOT been verified. "
                            "You MUST run './gradlew build' to verify your changes compile. "
                            "Do not finish until the build passes."
                        )
                    })
                    # Continue the loop
                    continue
                else:
                    return True
    
    logger.error(f"❌ Task exceeded max iterations ({MAX_ITERATIONS})")
    return False


def main():
    """Main entry point for the Night Shift Agent."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  🌙 Night Shift Agent v2.0                                   ║
    ║  Autonomous Coding Assistant with Build Verification         ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    logger.info(f"🚀 Starting Night Shift Agent")
    logger.info(f"📝 Log file: {LOG_FILE}")
    logger.info(f"🤖 Model: {MODEL_NAME}")
    logger.info(f"🔧 Max iterations: {MAX_ITERATIONS}")
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
        print("Example:")
        print("  Add a loading spinner to the main screen")
        print("  [x] Completed tasks start with [x]")
        return
    
    # Process tasks
    with open("tasks.txt", "r") as f:
        lines = f.readlines()
    
    tasks_processed = 0
    tasks_succeeded = 0
    
    while True:
        # Reload tasks (in case file was modified)
        with open("tasks.txt", "r") as f:
            lines = f.readlines()
        
        # Find first unchecked task
        task_index = -1
        current_task = ""
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("[x]") and not stripped.startswith("#"):
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
            # Mark task as done
            lines[task_index] = f"[x] {lines[task_index].lstrip()}"
            with open("tasks.txt", "w") as f:
                f.writelines(lines)
            logger.info(f"✅ Marked task as done: {current_task}")
            tasks_succeeded += 1
        else:
            logger.error(f"❌ Task failed (not marked as done): {current_task}")
            # Add failure marker
            lines[task_index] = f"[!] {lines[task_index].lstrip()}"
            with open("tasks.txt", "w") as f:
                f.writelines(lines)
            logger.info("⏭️ Skipping to next task...")
        
        # Small delay between tasks
        time.sleep(2)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 Session Summary")
    logger.info(f"{'='*60}")
    logger.info(f"   Tasks processed: {tasks_processed}")
    logger.info(f"   Tasks succeeded: {tasks_succeeded}")
    logger.info(f"   Tasks failed:    {tasks_processed - tasks_succeeded}")
    logger.info(f"   Log file:        {LOG_FILE}")


if __name__ == "__main__":
    main()
