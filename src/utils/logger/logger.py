import inspect
import os
from datetime import datetime
from enum import Enum

from colorama import Fore, Style, init as colorama_init

colorama_init()


class LoggerLevel(str, Enum):
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"


class Logger:
    def __init__(self):
        self._log_format = (
            "{color}[{level}]--[{timestamp}]{reset} "
            "{module_color}({module}:{line}){reset}:  {message}"
        )
        self._module_color = Fore.LIGHTBLUE_EX

    def debug(self, message: str) -> None:
        self._log(message, LoggerLevel.debug, Fore.LIGHTGREEN_EX)

    def info(self, message: str) -> None:
        self._log(message, LoggerLevel.info, Fore.LIGHTYELLOW_EX)

    def warning(self, message: str) -> None:
        self._log(message, LoggerLevel.warning, Fore.YELLOW)

    def error(self, message: str) -> None:
        self._log(message, LoggerLevel.error, Fore.RED)

    def _log(self, message: str, level: LoggerLevel, color: str) -> None:
        frame = inspect.currentframe().f_back.f_back
        module_info = inspect.getmodule(frame)

        if module_info:
            module_path = module_info.__file__
            module_name = os.path.splitext(os.path.basename(module_path))[0]
        else:
            module_name = "unknown"

        # Получаем номер строки
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
            message=message.capitalize()
        )

        print(formatted_message)


logger = Logger()
