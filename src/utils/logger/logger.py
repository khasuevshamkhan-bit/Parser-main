import inspect
import os
from datetime import datetime

from colorama import Fore, Style, init as colorama_init

from src.utils.logger.enums.logger_enums import LoggerLevel

colorama_init()


class Logger:
    """
    Console logger with colored output and caller context.

    Provides debug, info, warning and error logging with automatic
    module name and line number detection.
    """

    def __init__(self) -> None:
        self._log_format = (
            "{color}[{level}]--[{timestamp}]{reset} "
            "{module_color}({module}:{line}){reset}:  {message}"
        )
        self._module_color = Fore.LIGHTBLUE_EX

    def debug(self, message: str) -> None:
        """
        Log a debug-level message.

        :param message: message content to log
        """

        self._log(message=message, level=LoggerLevel.debug, color=Fore.LIGHTGREEN_EX)

    def info(self, message: str) -> None:
        """
        Log an info-level message.

        :param message: message content to log
        """

        self._log(message=message, level=LoggerLevel.info, color=Fore.LIGHTYELLOW_EX)

    def warning(self, message: str) -> None:
        """
        Log a warning-level message.

        :param message: message content to log
        """

        self._log(message=message, level=LoggerLevel.warning, color=Fore.YELLOW)

    def error(self, message: str) -> None:
        """
        Log an error-level message.

        :param message: message content to log
        """

        self._log(message=message, level=LoggerLevel.error, color=Fore.RED)

    def exception(self, message: str) -> None:
        """
        Log an error-level message with the current exception context.

        The traceback of the active exception is appended to aid debugging.
        """

        import traceback

        formatted_traceback = traceback.format_exc()
        combined = f"{message}\n{formatted_traceback}" if formatted_traceback else message
        self._log(message=combined, level=LoggerLevel.error, color=Fore.RED)

    def _log(self, message: str, level: LoggerLevel, color: str) -> None:
        """
        Format and print a log message with caller context.

        :param message: message content to log
        :param level: log severity level
        :param color: ANSI color code for the level prefix
        """

        frame = inspect.currentframe().f_back.f_back
        module_info = inspect.getmodule(frame)

        if module_info and module_info.__file__:
            module_path = module_info.__file__
            module_name = os.path.splitext(os.path.basename(module_path))[0]
        else:
            module_name = "unknown"

        line_no = frame.f_lineno
        timestamp = datetime.now().replace(microsecond=0)

        formatted_message = self._log_format.format(
            color=color,
            level=level.value,
            timestamp=timestamp,
            reset=Style.RESET_ALL,
            module_color=self._module_color,
            module=module_name,
            line=line_no,
            message=message.capitalize(),
        )

        print(formatted_message)


logger = Logger()
