import os
import subprocess
import sys
import glob
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3-pro-latest"

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

def main():
    print("🌙 Night Shift Agent Initializing...")
    model = setup_gemini()
    chat = model.start_chat(enable_automatic_function_calling=True)
    print("✨ Connected to Gemini (with Tools).")

    # Check Task Queue
    if os.path.exists("tasks.txt"):
        with open("tasks.txt", "r") as f:
            tasks = [line.strip() for line in f.readlines() if line.strip()]
        
        if tasks:
            current_task = tasks[0]
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
            
            Go!
            """
            
            try:
                # The chat session handles the tool loop automatically with enable_automatic_function_calling=True
                response = chat.send_message(prompt)
                print(f"\n🧠 Agent Report:\n{response.text}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("Task queue is empty.")
    else:
        print("No tasks.txt found.")

if __name__ == "__main__":
    main()
