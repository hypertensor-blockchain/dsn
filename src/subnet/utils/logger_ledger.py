import logging
import os

class LoggerLedger:
    CUSTOM_LEVEL = 25  # Define custom log level

    def __init__(self, log_file="debug.log"):
      logging.addLevelName(self.CUSTOM_LEVEL, "CUSTOM")
      logging.Logger.custom = self.custom_log

      self.logger = logging.getLogger(__name__)
      self.logger.propagate = False

      file_handler = logging.FileHandler(log_file)
      file_handler.setLevel(self.CUSTOM_LEVEL)
      file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
      file_handler.setFormatter(file_formatter)

      self.logger.addHandler(file_handler)

    def custom_log(self, message, *args, **kwargs):
      """Log using the CUSTOM level."""
      if self.logger.isEnabledFor(self.CUSTOM_LEVEL):
        self.logger._log(self.CUSTOM_LEVEL, message, args, **kwargs)

    def get_logger(self):
      """Return the logger instance"""
      return self.logger

# Create a global logger instance
logger_ledger = LoggerLedger().get_logger()
