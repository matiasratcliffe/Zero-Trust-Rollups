from colorama import Fore, Style
from datetime import datetime

class Logger:
    loggingActive = True
    def log(message, raw=False):
        message += Style.RESET_ALL + "\n"
        message = message if raw else f"[{datetime.now()}] {message}"
        if Logger.loggingActive:
            with open("logs.txt", "a", encoding='utf8') as f:
                f.write(Fore.GREEN + message)