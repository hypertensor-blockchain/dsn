
from tabulate import tabulate


def coldkey_input():
  confirm = input(
    "\n"
    f"Are you sure you want to proceed with using the same key for both hotkey and coldkey? "
    "\n"
    f"The hotkey is used for frequent operations such as validating and attesting and can be updated by the coldkey. "
    "\n"
    f"The coldkey is used for any operations including any movements of tokens such as staking. "
    "\n"
    f"Are you sure you want to proceed? (yes/no): "
    ).strip().lower()
  if confirm not in ["yes", "y"]:
    print("Action canceled. Expects 'yes' or 'y'")
    return

GREEN = '\033[32m'
RESET = '\033[0m'

def coldkey_delete_print():
  text = f"""
  {GREEN}Copy and paste the following to delete the last command from history, and double check it's deleted{RESET}.

  history -d -1;history -d -1;history -w
  """

  table = [[text]]
  output = tabulate(table, tablefmt='grid')
  print(output)
