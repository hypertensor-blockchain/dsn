# import logging
# from hypermind.utils.logging import get_logger
# logger = get_logger(__name__)

# class LoggerLedgerDebug:
#   def __init__(self, log_file="debug.log"):
#     # self.logger = logging.getLogger(__name__)
#     # self.logger.propagate = False
#     self.logger = logger
#     self.logger.setLevel(logging.DEBUG)

#     file_handler = logging.FileHandler(log_file)
#     file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
#     file_handler.setFormatter(file_formatter)

#     self.logger.addHandler(file_handler)

#   def get_logger(self):
#     """Return the logger instance"""
#     return self.logger

# logger = LoggerLedgerDebug().get_logger()
