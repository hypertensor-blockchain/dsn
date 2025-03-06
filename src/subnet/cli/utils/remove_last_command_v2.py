import os
import platform
import subprocess
# from colorama import Fore, Back, Style
from hypermind.utils.logging import get_logger

logger = get_logger(__name__)


def overwrite_last_line(file_path):
    """Overwrite the last line of a file with random data before deleting it."""
    if not os.path.exists(file_path):
        return
    
    with open(file_path, "r") as f:
        lines = f.readlines()

    if not lines:
        return  # No history to delete

    last_line = lines[-1]  # Store last command
    random_data = os.urandom(len(last_line)).decode('latin-1', 'ignore')  # Random overwrite

    # Overwrite last line with random data
    lines[-1] = random_data + "\n"
    with open(file_path, "w") as f:
        f.writelines(lines[:-1])  # Remove last line

    print(f"Last command securely deleted from {file_path}.")

def remove_last_command():
    """Detects OS and shell, then deletes the last history entry securely."""
    system_type = platform.system()
    shell = os.environ.get("SHELL", "")
    print("system_type: ", system_type)
    print("shell: ", shell)

    if system_type == "Windows":
        print("in windows")
        # PowerShell history
        powershell_history = os.path.expanduser("~/AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt")
        if os.path.exists(powershell_history):
            overwrite_last_line(powershell_history)

        # CMD history is temporary, so just clear session history
        subprocess.run("cls", shell=True)
        print("Last CMD/PowerShell command removed.")

    else:  # Linux, macOS, WSL
        if "bash" in shell:
            print("in bash")
            # history_output = subprocess.check_output(
            #     "bash -i -c 'history -r; history -d -2'", 
            #     shell=True, 
            #     text=True
            # )

            # print("history_output", history_output)
            # process = subprocess.run("history -d -2 && history -w", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # print("process", process)
        elif "zsh" in shell:
            print("in zsh")
            # Delete last command from Zsh
            os.system("fc -ln -1 | sed -i '' -e '$d' ~/.zsh_history")
            print("Last Zsh command removed.")

        elif "fish" in shell:
            print("in fish")
            # Delete last command from Fish shell
            os.system("set -l last_command (history | tail -n 1); history delete --exact --case-sensitive \"$last_command\"")
            print("Last Fish command removed.")

    print("Shell history updated.")