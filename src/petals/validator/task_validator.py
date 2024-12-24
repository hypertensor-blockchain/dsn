import threading

class TaskValidator(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        ...