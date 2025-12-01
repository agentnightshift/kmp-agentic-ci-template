import os
import subprocess
import sys
import time
import glob
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"

# --- TOOLS ---

def read_file(filepath: str):
    """Reads a file and returns its content."""
    print(f"📖 Reading: {filepath}")
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {filepath}: {e}"

def write_file(filepath: str, content: str):
    """Writes content to a file. Overwrites if exists."""
    print(f"✍️ Writing to: {filepath}")
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing to {filepath}: {e}"

def list_files(directory: str = "."):
    """Lists files in a directory (recursive)."""
    print(f"📂 Listing: {directory}")
    file_list = []
    for root, dirs, files in os.walk(directory):
        if '.git' in dirs: dirs.remove('.git')
        if '.gradle' in dirs: dirs.remove('.gradle')
        if 'build' in dirs: dirs.remove('build')
        if '.idea' in dirs: dirs.remove('.idea')
        if '.venv' in dirs: dirs.remove('.venv')
        
        for file in files:
            path = os.path.relpath(os.path.join(root, file), directory)
            file_list.append(path)
    return "\n".join(file_list)

def run_shell(command: str):
    """Executes a shell command and returns output."""
    print(f"🤖 Executing: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            return f"✅ Output:\n{result.stdout}"
        else:
            return f"❌ Error (Exit Code {result.returncode}):\n{result.stderr}"
    except Exception as e:
        return f"❌ Exception: {str(e)}"

# --- AGENT SETUP ---

def setup_gemini():
    if not API_KEY:
        print("❌ Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)
    
    genai.configure(api_key=API_KEY)
    
    # Define Tools
    tools = [
        read_file,
        write_file,
        list_files,
        run_shell
    ]
    
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        tools=tools
    )

def send_message_with_retry(chat, prompt, max_retries=5):
    """Sends a message to Gemini with exponential backoff for rate limits."""
    delay = 2
    for attempt in range(max_retries):
        try:
            return chat.send_message(prompt)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                print(f"⚠️ Rate limit hit. Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                raise e
    raise Exception("Max retries exceeded for rate limit.")

def main():
    print("🌙 Night Shift Agent Initializing...")
    model = setup_gemini()
    chat = model.start_chat(enable_automatic_function_calling=True)
    print("✨ Connected to Gemini (with Tools).")

    # Check Task Queue
    if os.path.exists("tasks.txt"):
        while True:
            with open("tasks.txt", "r") as f:
                lines = f.readlines()
            
            # Find first unchecked task
            task_index = -1
            current_task = ""
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith("[x]"):
                    task_index = i
                    current_task = line.strip()
                    break
            
            if task_index != -1:
                print(f"\n▶️ Processing Task: {current_task}")
                
                # Load Context
                architecture_guide = ""
                if os.path.exists("ARCHITECTURE.md"):
                    architecture_guide = read_file("ARCHITECTURE.md")
                
                project_files = list_files()

                prompt = f"""You are the Night Shift Agent, an autonomous coding assistant.
                
                SYSTEM INSTRUCTIONS:
                {architecture_guide}
                
                PROJECT FILES:
                {project_files}
                
                TASK:
                {current_task}
                
                INSTRUCTIONS:
                1. Analyze the task.
                2. Read necessary files to understand the code.
                3. Modify or create files using 'write_file'.
                4. Verify your work using 'run_shell' (e.g., run tests).
                5. If verification fails, fix the code and retry.
                6. Commit your changes using 'run_shell' (e.g., git commit).
                
                Go!
                """
                
                try:
                    # Use the retry wrapper
                    response = send_message_with_retry(chat, prompt)
                    print(f"\n🧠 Agent Report:\n{response.text}")
                    
                    # Mark task as done if successful (assuming no exception)
                    lines[task_index] = f"[x] {lines[task_index]}"
                    with open("tasks.txt", "w") as f:
                        f.writelines(lines)
                    print(f"✅ Marked task as done: {current_task}")
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                    break # Stop on error to avoid infinite loops or broken state
            else:
                print("Task queue is empty (all tasks completed).")
                break
    else:
        print("No tasks.txt found.")

if __name__ == "__main__":
    main()
