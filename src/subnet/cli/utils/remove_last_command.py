import os
import sys
import readline
import subprocess
from hypermind.utils.logging import get_logger

logger = get_logger(__name__)

def remove_last_command():
    """Removes only the last executed command (the script invocation) from the shell history."""

    shell = os.getenv("SHELL", "")
    python_command = " ".join(sys.argv)  # The exact command that ran this script

    if "bash" in shell:
        # Remove last command from current session
        readline.remove_history_item(readline.get_current_history_length() - 1)
        # Rewrite the history file without the last command
        subprocess.run("history -d $(history 1); history -w", shell=True)

    elif "zsh" in shell:
        # Remove from Zsh history file
        subprocess.run("fc -ln -1 | sed -i '' -e '$d' ~/.zsh_history", shell=True)
        subprocess.run("history -p > ~/.zsh_history", shell=True)

    elif "fish" in shell:
        # Fish shell clears history using `history delete`
        subprocess.run(f"history delete --exact '{python_command}'", shell=True)

    elif os.name == "nt":
        # Windows CMD (Clearing command history)
        subprocess.run("doskey /reinstall", shell=True)
        
        # Windows PowerShell
        subprocess.run("Clear-History", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    else:
        logger.warning(
            "Last command not deleted. Shell history clearing not supported for this shell. "
            "If you're seeing this message it's because you likely entered sensitive information. "
            "If the previous command utilized sensitive information, delete it from your command history. "
        )